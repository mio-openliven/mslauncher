from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from generate_manifest import generate_build_config, generate_manifest, validate_loader, validate_port, write_json
from inspect_client_pack import (
    ClientPackInspectionError,
    FolderSources,
    InspectionReport,
    analyze_client_pack,
    extract_archive,
    likely_versions,
    safe_archive_name,
)


DEFAULT_PREPARE_REPORT = PROJECT_ROOT / "release" / "client_pack_prepare_report.md"
SUPPORTED_RELEASE_LOADERS = ("vanilla", "fabric", "quilt", "neoforge")
KNOWN_LOADERS = ("vanilla", "fabric", "quilt", "forge", "neoforge")
UNKNOWN_VALUES = ("", "unknown", "unknown_if_needed", "auto")
COPY_ROOTS = ("mods", "config", "resourcepacks")
SKIPPED_FILE_NAMES = {
    ".gitkeep",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "launcher_config.json",
    "MSLauncher.exe",
    "MSLaunch.exe",
    "build_exe.ps1",
    "MSLauncher.spec",
}
SKIPPED_SUFFIXES = (".part", ".tmp")


class PrepareClientPackError(RuntimeError):
    pass


@dataclass
class PrepareResult:
    archive: Path
    output_dir: Path
    base_url: str
    status: str = "ok"
    error: str = ""
    loader: str = ""
    minecraft_version: str = ""
    loader_version: str = "latest"
    build_name: str = "Main Server"
    server: str = ""
    port: str = ""
    copied_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_files: list[str] = field(default_factory=list)
    analyzer_loader: str = "unknown"
    analyzer_confidence: str = "low"
    analyzer_versions: list[tuple[str, int]] = field(default_factory=list)


def normalize_optional_value(value: str) -> str:
    cleaned = value.strip()
    return "" if cleaned.lower() in UNKNOWN_VALUES else cleaned


def choose_loader(raw_loader: str, report: InspectionReport) -> str:
    explicit_loader = normalize_optional_value(raw_loader).lower()
    if explicit_loader:
        if explicit_loader not in KNOWN_LOADERS:
            raise PrepareClientPackError("Loader must be fabric, quilt, forge, neoforge, or vanilla.")
        loader = explicit_loader
    else:
        if report.loader_guess == "unknown" or report.confidence != "high":
            raise PrepareClientPackError(
                "Loader is unknown. Pass --loader fabric/quilt/neoforge/vanilla after confirming with the client."
            )
        loader = report.loader_guess

    if loader == "forge":
        raise PrepareClientPackError(
            "Forge packs still need a separate release pass. Use Quilt/NeoForge/Fabric/Vanilla only for this launcher pass."
        )
    if loader not in SUPPORTED_RELEASE_LOADERS:
        raise PrepareClientPackError("This launcher currently supports vanilla/fabric/quilt/neoforge.")
    return loader


def choose_minecraft_version(raw_version: str, report: InspectionReport) -> str:
    explicit_version = normalize_optional_value(raw_version)
    if explicit_version:
        return explicit_version

    versions = likely_versions(report)
    if not versions:
        raise PrepareClientPackError(
            "Minecraft version is unknown. Pass --minecraft-version 1.20.1 after confirming with the client."
        )

    top_version, top_count = versions[0]
    second_count = versions[1][1] if len(versions) > 1 else 0
    if report.confidence == "high" and (top_count > second_count or len(versions) == 1):
        return top_version

    raise PrepareClientPackError(
        "Minecraft version is unknown. Pass --minecraft-version 1.20.1 after confirming with the client."
    )


def should_skip_copy(file_path: Path) -> bool:
    if file_path.name in SKIPPED_FILE_NAMES:
        return True
    if any(file_path.name.endswith(suffix) for suffix in SKIPPED_SUFFIXES):
        return True
    lowered_parts = {part.lower() for part in file_path.parts}
    if ".mslauncher-staging" in lowered_parts or "__pycache__" in lowered_parts:
        return True
    if "dist" in lowered_parts or "build" in lowered_parts:
        return True
    return False


def clean_output_dir(output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for folder_name in COPY_ROOTS:
        target = (output_dir / folder_name).resolve()
        ensure_inside(output_dir, target)
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
    for file_name in ("manifest.json", "build.json"):
        target_file = (output_dir / file_name).resolve()
        ensure_inside(output_dir, target_file)
        if target_file.exists():
            target_file.unlink()


def ensure_inside(root: Path, target: Path) -> None:
    root = root.resolve()
    target = target.resolve()
    if root not in (target, *target.parents):
        raise PrepareClientPackError(f"Refusing to operate outside output-dir: {target}")


def copy_file(source: Path, destination: Path, output_dir: Path, result: PrepareResult) -> None:
    if should_skip_copy(source):
        result.skipped_files.append(source.name)
        return
    safe_archive_name(destination.relative_to(output_dir).as_posix())
    ensure_inside(output_dir, destination)
    if destination.exists():
        result.skipped_files.append(destination.relative_to(output_dir).as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    result.copied_files.append(destination.relative_to(output_dir).as_posix())


def copy_tree_contents(source: Path, target: Path, output_dir: Path, result: PrepareResult) -> None:
    source = source.resolve()
    for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
        relative_path = file_path.relative_to(source)
        destination = (target / relative_path).resolve()
        copy_file(file_path, destination, output_dir, result)


def copy_sources(sources: FolderSources, output_dir: Path, result: PrepareResult) -> None:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for folder_name in COPY_ROOTS:
        (output_dir / folder_name).mkdir(parents=True, exist_ok=True)

    if sources.mods:
        if sources.mode == "jar_directory_only":
            for jar_path in sorted(path for path in sources.mods.glob("*.jar") if path.is_file()):
                copy_file(jar_path, (output_dir / "mods" / jar_path.name).resolve(), output_dir, result)
        else:
            copy_tree_contents(sources.mods, output_dir / "mods", output_dir, result)
    if sources.config:
        copy_tree_contents(sources.config, output_dir / "config", output_dir, result)
    if sources.resourcepacks:
        copy_tree_contents(sources.resourcepacks, output_dir / "resourcepacks", output_dir, result)


def generate_server_pack_files(
    *,
    output_dir: Path,
    base_url: str,
    build_name: str,
    minecraft_version: str,
    loader: str,
    loader_version: str,
    server: str,
    port: str,
    result: PrepareResult,
) -> None:
    try:
        validate_loader(loader)
        validate_port(port)
    except ValueError as exc:
        raise PrepareClientPackError(str(exc)) from exc

    manifest = generate_manifest(output_dir, base_url)
    build = generate_build_config(
        build_name=build_name,
        minecraft_version=minecraft_version,
        loader=loader,
        loader_version=loader_version,
        base_url=base_url,
        output_manifest="manifest.json",
        server=server,
        port=port,
    )
    manifest_path = output_dir / "manifest.json"
    build_path = output_dir / "build.json"
    write_json(manifest_path, manifest)
    write_json(build_path, build)
    result.generated_files.extend([manifest_path.name, build_path.name])


def render_prepare_report(result: PrepareResult) -> str:
    warnings = "\n".join(f"- {warning}" for warning in result.warnings) or "- none"
    copied = "\n".join(f"- `{path}`" for path in result.copied_files[:160]) or "- none"
    skipped = "\n".join(f"- `{path}`" for path in result.skipped_files[:160]) or "- none"
    generated = "\n".join(f"- `{path}`" for path in result.generated_files) or "- none"
    versions = ", ".join(f"{version} ({count})" for version, count in result.analyzer_versions[:10]) or "unknown"
    error_block = f"\n## Error\n\n{result.error}\n" if result.error else ""
    return (
        "# Client Pack Prepare Report\n\n"
        f"- Archive: `{result.archive}`\n"
        f"- Output dir: `{result.output_dir}`\n"
        f"- Status: `{result.status}`\n"
        f"- Base URL: `{result.base_url}`\n"
        f"- Analyzer loader: `{result.analyzer_loader}` / confidence `{result.analyzer_confidence}`\n"
        f"- Analyzer versions: `{versions}`\n"
        f"- Loader used: `{result.loader or 'unknown'}`\n"
        f"- Minecraft version used: `{result.minecraft_version or 'unknown'}`\n"
        f"- Build name: `{result.build_name}`\n"
        f"- Server: `{result.server or 'not set'}`\n"
        f"- Port: `{result.port or 'not set'}`\n"
        f"- Copied files count: `{len(result.copied_files)}`\n"
        f"{error_block}\n"
        "## Warnings\n\n"
        f"{warnings}\n\n"
        "## Copied Files\n\n"
        f"{copied}\n\n"
        "## Skipped Files\n\n"
        f"{skipped}\n\n"
        "## Generated Files\n\n"
        f"{generated}\n\n"
        "## Next Commands\n\n"
        "Run these in the separate public modpack repository, not necessarily in the launcher repo:\n\n"
        "```powershell\n"
        "git add server_pack\n"
        "git commit -m \"Update Nukem modpack\"\n"
        "git push\n"
        "```\n\n"
        "After publishing, update launcher `source_key` to the public raw `build.json` URL.\n"
    )


def write_prepare_report(path: Path, result: PrepareResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_prepare_report(result), encoding="utf-8")


def prepare_server_pack(
    *,
    archive_path: Path,
    output_dir: Path,
    base_url: str,
    minecraft_version: str = "",
    loader: str = "",
    loader_version: str = "latest",
    build_name: str = "Main Server",
    server: str = "",
    port: str = "",
    clean: bool = False,
    report_path: Path = DEFAULT_PREPARE_REPORT,
) -> PrepareResult:
    archive_path = archive_path.resolve()
    output_dir = output_dir.resolve()
    result = PrepareResult(
        archive=archive_path,
        output_dir=output_dir,
        base_url=base_url.rstrip("/"),
        loader_version=loader_version.strip() or "latest",
        build_name=build_name.strip() or "Main Server",
        server=server.strip(),
        port=str(port).strip(),
    )

    try:
        if not archive_path.is_file():
            raise PrepareClientPackError("Archive file does not exist.")
        if not result.base_url:
            raise PrepareClientPackError("base-url is required.")

        with tempfile.TemporaryDirectory(prefix="mslaunch-prepare-") as temp_dir:
            temp_root = Path(temp_dir)
            try:
                extract_archive(archive_path, temp_root)
                inspection, sources = analyze_client_pack(archive_path, temp_root)
            except ClientPackInspectionError as exc:
                raise PrepareClientPackError(str(exc)) from exc

            result.analyzer_loader = inspection.loader_guess
            result.analyzer_confidence = inspection.confidence
            result.analyzer_versions = likely_versions(inspection)
            result.warnings.extend(inspection.suspicious_files[:12])

            result.loader = choose_loader(loader, inspection)
            result.minecraft_version = choose_minecraft_version(minecraft_version, inspection)

            if clean:
                clean_output_dir(output_dir)
            else:
                output_dir.mkdir(parents=True, exist_ok=True)

            copy_sources(sources, output_dir, result)
            generate_server_pack_files(
                output_dir=output_dir,
                base_url=result.base_url,
                build_name=result.build_name,
                minecraft_version=result.minecraft_version,
                loader=result.loader,
                loader_version=result.loader_version,
                server=result.server,
                port=result.port,
                result=result,
            )
    except PrepareClientPackError as exc:
        result.status = "failed"
        result.error = str(exc)
        result.warnings.append(str(exc))
        write_prepare_report(report_path, result)
        raise

    write_prepare_report(report_path, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare server_pack from a client Minecraft modpack archive.")
    parser.add_argument("--archive", required=True, help="Path to .zip or .rar archive.")
    parser.add_argument("--output-dir", required=True, help="Target server_pack directory.")
    parser.add_argument("--base-url", required=True, help="Raw base URL for manifest file URLs.")
    parser.add_argument("--minecraft-version", default="", help="Minecraft version. If omitted, high-confidence analyzer result is used.")
    parser.add_argument("--loader", default="", help="Loader: vanilla, fabric, quilt, or neoforge. Forge is rejected for this pass.")
    parser.add_argument("--loader-version", default="latest", help="Loader version for build.json.")
    parser.add_argument("--build-name", default="Main Server", help="Build name for build.json.")
    parser.add_argument("--server", default="", help="Minecraft server address for build.json.")
    parser.add_argument("--port", default="", help="Minecraft server port for build.json.")
    parser.add_argument("--clean", action="store_true", help="Clean only mods/config/resourcepacks and manifest/build in output-dir first.")
    parser.add_argument("--report", default=str(DEFAULT_PREPARE_REPORT), help="Markdown prepare report path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = prepare_server_pack(
            archive_path=Path(args.archive),
            output_dir=Path(args.output_dir),
            base_url=args.base_url,
            minecraft_version=args.minecraft_version,
            loader=args.loader,
            loader_version=args.loader_version,
            build_name=args.build_name,
            server=args.server,
            port=args.port,
            clean=args.clean,
            report_path=Path(args.report),
        )
    except PrepareClientPackError as exc:
        print(f"Client server_pack prepare failed: {exc}", file=sys.stderr)
        print(f"Report written to: {args.report}", file=sys.stderr)
        return 2

    print("Client server_pack prepare: OK")
    print(f"loader={result.loader} minecraft_version={result.minecraft_version} copied={len(result.copied_files)}")
    print(f"Report written to: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
