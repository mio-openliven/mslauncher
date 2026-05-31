from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = PROJECT_ROOT / "release" / "client_pack_report.md"
SCAN_FOLDERS = ("mods", "config", "resourcepacks")
MINECRAFT_VERSION_PATTERN = re.compile(r"(?<!\d)(1\.\d{1,2}(?:\.\d+)?)(?!\d)")


class ClientPackInspectionError(RuntimeError):
    pass


@dataclass
class FolderSources:
    mods: Path | None = None
    config: Path | None = None
    resourcepacks: Path | None = None
    mode: str = "unknown"


@dataclass
class ModInfo:
    path: str
    loader_markers: set[str] = field(default_factory=set)
    mod_ids: set[str] = field(default_factory=set)
    minecraft_versions: set[str] = field(default_factory=set)
    readable: bool = True
    note: str = ""


@dataclass
class InspectionReport:
    archive: Path
    status: str = "ok"
    error: str = ""
    loader_guess: str = "unknown"
    confidence: str = "low"
    possible_versions: set[str] = field(default_factory=set)
    found_folders: list[str] = field(default_factory=list)
    mod_infos: list[ModInfo] = field(default_factory=list)
    suspicious_files: list[str] = field(default_factory=list)
    unsupported_files: list[str] = field(default_factory=list)
    resource_pack_formats: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    extracted_files: list[str] = field(default_factory=list)
    skipped_existing_files: list[str] = field(default_factory=list)

    @property
    def mod_count(self) -> int:
        return len(self.mod_infos)


@dataclass(frozen=True)
class RarExtractor:
    kind: str
    path: Path


def safe_archive_name(name: str) -> str:
    normalized = name.replace("\\", "/").strip()
    if not normalized:
        raise ClientPackInspectionError("Archive contains an empty path.")
    if normalized.startswith("/"):
        raise ClientPackInspectionError(f"Archive contains an absolute path: {name}")
    if PureWindowsPath(normalized).drive:
        raise ClientPackInspectionError(f"Archive contains a drive path: {name}")

    parts = PurePosixPath(normalized).parts
    if any(part in ("..", "") for part in parts):
        raise ClientPackInspectionError(f"Archive contains an unsafe path: {name}")
    return normalized


def safe_extract_zip(archive_path: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                safe_name = safe_archive_name(member.filename)
                target = (destination / safe_name).resolve()
                if destination.resolve() not in (target, *target.parents):
                    raise ClientPackInspectionError(f"Archive path escapes extraction folder: {member.filename}")
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except zipfile.BadZipFile as exc:
        raise ClientPackInspectionError("ZIP archive is damaged or unsupported.") from exc


def default_rar_candidates() -> list[Path]:
    names = ("7z.exe", "7za.exe", "UnRAR.exe", "WinRAR.exe")
    candidates: list[Path] = []
    for name in names:
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))

    roots = [
        Path("C:/Program Files/7-Zip"),
        Path("C:/Program Files (x86)/7-Zip"),
        Path("C:/Program Files/WinRAR"),
        Path("C:/Program Files (x86)/WinRAR"),
    ]
    for root in roots:
        for name in names:
            candidates.append(root / name)
    return candidates


def find_rar_extractor(candidates: list[Path] | None = None) -> RarExtractor | None:
    for candidate in candidates if candidates is not None else default_rar_candidates():
        if not candidate.is_file():
            continue
        name = candidate.name.lower()
        if name in ("7z.exe", "7za.exe"):
            return RarExtractor("7z", candidate)
        if name == "unrar.exe":
            return RarExtractor("unrar", candidate)
        if name == "winrar.exe":
            return RarExtractor("winrar", candidate)
    return None


def run_process(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def list_rar_paths(archive_path: Path, extractor: RarExtractor) -> list[str]:
    if extractor.kind == "7z":
        result = run_process([str(extractor.path), "l", "-slt", str(archive_path)])
        if result.returncode != 0:
            raise ClientPackInspectionError(f"Could not list RAR archive with 7-Zip: {result.stderr.strip()}")
        paths = []
        for line in result.stdout.splitlines():
            if line.startswith("Path = "):
                value = line.removeprefix("Path = ").strip()
                if value and Path(value) != archive_path:
                    paths.append(value)
        return paths

    command = "lb"
    result = run_process([str(extractor.path), command, str(archive_path)])
    if result.returncode != 0:
        raise ClientPackInspectionError(f"Could not list RAR archive: {result.stderr.strip() or result.stdout.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def safe_extract_rar(archive_path: Path, destination: Path, rar_candidates: list[Path] | None = None) -> None:
    extractor = find_rar_extractor(rar_candidates)
    if extractor is None:
        raise ClientPackInspectionError("RAR archive requires 7-Zip, WinRAR, or UnRAR. Install 7-Zip or ask the client to send .zip.")

    archive_paths = list_rar_paths(archive_path, extractor)
    for archive_name in archive_paths:
        safe_archive_name(archive_name)

    if extractor.kind == "7z":
        result = run_process([str(extractor.path), "x", "-y", f"-o{destination}", str(archive_path)])
    else:
        result = run_process([str(extractor.path), "x", "-y", str(archive_path), str(destination)])
    if result.returncode != 0:
        raise ClientPackInspectionError(f"Could not extract RAR archive: {result.stderr.strip() or result.stdout.strip()}")


def extract_archive(archive_path: Path, destination: Path, rar_candidates: list[Path] | None = None) -> None:
    suffix = archive_path.suffix.lower()
    if suffix == ".zip":
        safe_extract_zip(archive_path, destination)
        return
    if suffix == ".rar":
        safe_extract_rar(archive_path, destination, rar_candidates)
        return
    raise ClientPackInspectionError("Unsupported archive type. Ask the client for .zip or .rar.")


def find_folder_sources(root: Path) -> FolderSources:
    candidates: list[tuple[int, FolderSources]] = []
    bases = [root, *[path for path in root.rglob("*") if path.is_dir()]]
    for base in bases:
        direct_mods = base / "mods"
        minecraft_mods = base / ".minecraft" / "mods"
        mods_dir = direct_mods if direct_mods.is_dir() else minecraft_mods if minecraft_mods.is_dir() else None
        config_dir = base / "config"
        if not config_dir.is_dir():
            minecraft_config = base / ".minecraft" / "config"
            config_dir = minecraft_config if minecraft_config.is_dir() else None
        resourcepacks_dir = base / "resourcepacks"
        if not resourcepacks_dir.is_dir():
            minecraft_resourcepacks = base / ".minecraft" / "resourcepacks"
            resourcepacks_dir = minecraft_resourcepacks if minecraft_resourcepacks.is_dir() else None

        score = 0
        if mods_dir:
            score += 10 + count_jars(mods_dir)
        if config_dir:
            score += 2
        if resourcepacks_dir:
            score += 2
        if score:
            candidates.append((score, FolderSources(mods_dir, config_dir, resourcepacks_dir, "standard")))

    if candidates:
        return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]

    jar_dirs: list[tuple[int, Path]] = []
    for directory in bases:
        jar_count = len(list(directory.glob("*.jar")))
        if jar_count:
            jar_dirs.append((jar_count, directory))
    if jar_dirs:
        jar_dir = sorted(jar_dirs, key=lambda item: item[0], reverse=True)[0][1]
        return FolderSources(mods=jar_dir, mode="jar_directory_only")

    return FolderSources()


def count_jars(folder: Path) -> int:
    return len([path for path in folder.rglob("*.jar") if path.is_file()])


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def analyze_client_pack(archive_path: Path, extracted_root: Path) -> tuple[InspectionReport, FolderSources]:
    report = InspectionReport(archive=archive_path)
    sources = find_folder_sources(extracted_root)
    for folder in (sources.mods, sources.config, sources.resourcepacks):
        if folder:
            report.found_folders.append(relative_to_root(folder, extracted_root))

    analyze_manifest_files(extracted_root, report)
    analyze_resourcepacks(sources.resourcepacks, report)
    analyze_mods(sources.mods, extracted_root, report)
    find_suspicious_files(extracted_root, sources, report)
    guess_loader(report)
    build_recommendations(report, sources)
    return report, sources


def analyze_manifest_files(root: Path, report: InspectionReport) -> None:
    for file_name in ("manifest.json", "build.json"):
        for path in root.rglob(file_name):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                report.unsupported_files.append(f"{relative_to_root(path, root)}: unreadable JSON")
                continue
            if not isinstance(data, dict):
                continue
            minecraft_version = data.get("minecraft_version")
            if isinstance(minecraft_version, str) and minecraft_version.strip():
                report.possible_versions.add(minecraft_version.strip())
            loader = data.get("loader")
            if isinstance(loader, str) and loader.strip():
                report.suspicious_files.append(f"{relative_to_root(path, root)} declares loader={loader.strip()}")
            minecraft = data.get("minecraft")
            if isinstance(minecraft, dict):
                version = minecraft.get("version")
                if isinstance(version, str) and version.strip():
                    report.possible_versions.add(version.strip())
                for loader_item in minecraft.get("modLoaders", []):
                    if isinstance(loader_item, dict):
                        loader_id = str(loader_item.get("id", "")).lower()
                        if loader_id:
                            report.suspicious_files.append(f"{relative_to_root(path, root)} declares loader={loader_id}")


def analyze_resourcepacks(resourcepacks_dir: Path | None, report: InspectionReport) -> None:
    if not resourcepacks_dir:
        return
    for pack_meta in resourcepacks_dir.rglob("pack.mcmeta"):
        try:
            data = json.loads(pack_meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report.unsupported_files.append(f"{pack_meta.name}: unreadable pack.mcmeta")
            continue
        pack = data.get("pack") if isinstance(data, dict) else None
        pack_format = pack.get("pack_format") if isinstance(pack, dict) else None
        if pack_format is not None:
            report.resource_pack_formats.append(str(pack_format))


def analyze_mods(mods_dir: Path | None, root: Path, report: InspectionReport) -> None:
    if not mods_dir:
        return
    for jar_path in sorted(path for path in mods_dir.rglob("*.jar") if path.is_file()):
        info = analyze_jar(jar_path, root)
        report.mod_infos.append(info)
        report.possible_versions.update(info.minecraft_versions)


def analyze_jar(jar_path: Path, root: Path) -> ModInfo:
    info = ModInfo(path=relative_to_root(jar_path, root))
    info.minecraft_versions.update(extract_versions_from_text(jar_path.name))
    try:
        with zipfile.ZipFile(jar_path) as jar_file:
            names = set(jar_file.namelist())
            if "fabric.mod.json" in names:
                info.loader_markers.add("fabric")
                analyze_fabric_mod_json(jar_file, info)
            if "META-INF/mods.toml" in names:
                info.loader_markers.add("forge")
                analyze_mods_toml(jar_file, "META-INF/mods.toml", info)
            if "META-INF/neoforge.mods.toml" in names:
                info.loader_markers.add("neoforge")
                analyze_mods_toml(jar_file, "META-INF/neoforge.mods.toml", info)
    except zipfile.BadZipFile:
        info.readable = False
        info.note = "not a readable zip/jar"
    except OSError as exc:
        info.readable = False
        info.note = str(exc)
    return info


def analyze_fabric_mod_json(jar_file: zipfile.ZipFile, info: ModInfo) -> None:
    try:
        data = json.loads(jar_file.read("fabric.mod.json").decode("utf-8", errors="replace"))
    except (KeyError, json.JSONDecodeError):
        info.note = "unreadable fabric.mod.json"
        return
    if isinstance(data, dict):
        mod_id = data.get("id")
        if isinstance(mod_id, str):
            info.mod_ids.add(mod_id)
        depends = data.get("depends")
        if isinstance(depends, dict):
            minecraft_dep = depends.get("minecraft")
            info.minecraft_versions.update(extract_versions_from_dependency(minecraft_dep))


def analyze_mods_toml(jar_file: zipfile.ZipFile, toml_path: str, info: ModInfo) -> None:
    try:
        text = jar_file.read(toml_path).decode("utf-8", errors="replace")
    except KeyError:
        return
    info.minecraft_versions.update(extract_versions_from_text(text))
    mod_id_match = re.search(r'modId\s*=\s*"([^"]+)"', text)
    if mod_id_match:
        info.mod_ids.add(mod_id_match.group(1))


def extract_versions_from_dependency(value: object) -> set[str]:
    versions: set[str] = set()
    if isinstance(value, str):
        versions.update(extract_versions_from_text(value))
    elif isinstance(value, list):
        for item in value:
            versions.update(extract_versions_from_dependency(item))
    return versions


def extract_versions_from_text(text: str) -> set[str]:
    return set(MINECRAFT_VERSION_PATTERN.findall(text))


def find_suspicious_files(root: Path, sources: FolderSources, report: InspectionReport) -> None:
    mods_root = sources.mods.resolve() if sources.mods else None
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        relative_path = relative_to_root(path, root)
        if suffix in (".exe", ".bat", ".cmd", ".ps1", ".scr", ".msi"):
            report.suspicious_files.append(f"{relative_path}: executable/script file")
        if suffix == ".jar" and mods_root and mods_root not in (path.resolve(), *path.resolve().parents):
            report.suspicious_files.append(f"{relative_path}: jar outside mods folder")


def guess_loader(report: InspectionReport) -> None:
    fabric_count = sum(1 for mod in report.mod_infos if "fabric" in mod.loader_markers)
    forge_count = sum(1 for mod in report.mod_infos if "forge" in mod.loader_markers)
    neoforge_count = sum(1 for mod in report.mod_infos if "neoforge" in mod.loader_markers)
    exclusive_fabric = sum(1 for mod in report.mod_infos if mod.loader_markers == {"fabric"})
    exclusive_forge = sum(1 for mod in report.mod_infos if mod.loader_markers == {"forge"})
    exclusive_neoforge = sum(1 for mod in report.mod_infos if mod.loader_markers == {"neoforge"})
    mixed_count = sum(1 for mod in report.mod_infos if len(mod.loader_markers) > 1)
    fabric_api = any("fabric-api" in mod.mod_ids or "fabric-api" in mod.path.lower() for mod in report.mod_infos)

    exclusive_loaders = [
        name
        for name, count in (("fabric", exclusive_fabric), ("forge", exclusive_forge), ("neoforge", exclusive_neoforge))
        if count
    ]
    if len(exclusive_loaders) > 1:
        report.loader_guess = "unknown"
        report.confidence = "low"
        report.suspicious_files.append(f"conflicting exclusive loader markers: {', '.join(exclusive_loaders)}")
        return

    if exclusive_fabric or (fabric_count and not exclusive_forge and not exclusive_neoforge):
        report.loader_guess = "fabric"
        report.confidence = "high" if fabric_api else "medium"
        if mixed_count:
            report.suspicious_files.append(f"{mixed_count} jar(s) contain multi-loader metadata; Fabric still dominates.")
        return
    if exclusive_neoforge or (neoforge_count and not exclusive_fabric and not exclusive_forge):
        report.loader_guess = "neoforge"
        report.confidence = "high" if neoforge_count >= 2 else "medium"
        if mixed_count:
            report.suspicious_files.append(f"{mixed_count} jar(s) contain multi-loader metadata; NeoForge still dominates.")
        return
    if exclusive_forge or (forge_count and not exclusive_fabric and not exclusive_neoforge):
        report.loader_guess = "forge"
        report.confidence = "high" if forge_count >= 2 else "medium"
        if mixed_count:
            report.suspicious_files.append(f"{mixed_count} jar(s) contain multi-loader metadata; Forge still dominates.")
        return
    if report.mod_count == 0 and report.found_folders:
        report.loader_guess = "vanilla"
        report.confidence = "low"
        return

    report.loader_guess = "unknown"
    report.confidence = "low"


def build_recommendations(report: InspectionReport, sources: FolderSources) -> None:
    versions = likely_versions(report)
    if report.loader_guess in ("fabric", "vanilla") and versions:
        report.recommendations.append(f"Use minecraft_version={versions[0][0]} and loader={report.loader_guess}.")
    elif report.loader_guess in ("forge", "neoforge"):
        report.recommendations.append(
            f"Detected {report.loader_guess}, but current MSLaunch release supports vanilla/fabric sync best. Ask whether Fabric is required or plan a Forge pass."
        )
    else:
        report.recommendations.append("Minecraft version or loader is unknown. Ask the client for exact Minecraft version and loader.")

    if sources.mods:
        report.recommendations.append("Mods can be copied into server_pack/mods.")
    if sources.config:
        report.recommendations.append("Config can be copied into server_pack/config.")
    if sources.resourcepacks:
        report.recommendations.append("Resource packs can be copied into server_pack/resourcepacks.")
    if not report.mod_infos:
        report.recommendations.append("No mod jars found. Confirm whether the archive is only configs/resource packs or the wrong file.")
    if report.loader_guess == "fabric" and not any("fabric-api" in mod.mod_ids or "fabric-api" in mod.path.lower() for mod in report.mod_infos):
        report.recommendations.append("Fabric API was not detected. Ask if the pack needs fabric-api.")


def version_sort_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def likely_versions(report: InspectionReport) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for mod in report.mod_infos:
        for version in mod.minecraft_versions:
            counts[version] = counts.get(version, 0) + 1
    for version in report.possible_versions:
        counts.setdefault(version, 1)
    return sorted(counts.items(), key=lambda item: (-item[1], version_sort_key(item[0])))


def format_version_summary(report: InspectionReport) -> str:
    likely = likely_versions(report)
    if not likely:
        return "unknown"
    return ", ".join(f"{version} ({count})" for version, count in likely[:12])


def copy_sources_to_server_pack(sources: FolderSources, target_root: Path, *, clean: bool, report: InspectionReport) -> None:
    target_root = target_root.resolve()
    mappings = (
        (sources.mods, target_root / "mods"),
        (sources.config, target_root / "config"),
        (sources.resourcepacks, target_root / "resourcepacks"),
    )
    for source, target in mappings:
        if not source:
            continue
        if clean:
            clear_allowed_target(target_root, target)
        copy_tree_contents(source, target, target_root, report)


def clear_allowed_target(root: Path, target: Path) -> None:
    target = target.resolve()
    if target.name not in SCAN_FOLDERS:
        raise ClientPackInspectionError(f"Refusing to clean unexpected folder: {target}")
    if root not in (target, *target.parents):
        raise ClientPackInspectionError(f"Refusing to clean outside extract target: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def copy_tree_contents(source: Path, target: Path, target_root: Path, report: InspectionReport) -> None:
    source = source.resolve()
    target.mkdir(parents=True, exist_ok=True)
    for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
        relative_path = file_path.relative_to(source)
        safe_archive_name(relative_path.as_posix())
        destination = (target / relative_path).resolve()
        if target_root not in (destination, *destination.parents):
            raise ClientPackInspectionError(f"Refusing to copy outside target: {destination}")
        if destination.exists():
            report.skipped_existing_files.append(destination.relative_to(target_root).as_posix())
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, destination)
        report.extracted_files.append(destination.relative_to(target_root).as_posix())


def render_report(report: InspectionReport) -> str:
    versions = format_version_summary(report)
    found_folders = "\n".join(f"- `{folder}`" for folder in report.found_folders) or "- none"
    suspicious = "\n".join(f"- {item}" for item in report.suspicious_files[:80]) or "- none"
    unsupported = "\n".join(f"- {item}" for item in report.unsupported_files[:80]) or "- none"
    recommendations = "\n".join(f"- {item}" for item in report.recommendations) or "- Ask the client for the exact Minecraft version and loader."
    mods = "\n".join(render_mod_line(mod) for mod in report.mod_infos[:120]) or "- none"
    pack_formats = ", ".join(report.resource_pack_formats) or "none"
    copied = "\n".join(f"- `{item}`" for item in report.extracted_files[:120]) or "- none"
    skipped = "\n".join(f"- `{item}`" for item in report.skipped_existing_files[:120]) or "- none"

    error_block = f"\n## Error\n\n{report.error}\n" if report.error else ""
    return (
        "# Client Pack Inspection Report\n\n"
        f"- Archive: `{report.archive}`\n"
        f"- Status: `{report.status}`\n"
        f"- Loader guess: `{report.loader_guess}`\n"
        f"- Confidence: `{report.confidence}`\n"
        f"- Possible Minecraft versions: `{versions}`\n"
        f"- Mod count: `{report.mod_count}`\n"
        f"- Resource pack formats: `{pack_formats}`\n"
        f"{error_block}\n"
        "## Found Folders\n\n"
        f"{found_folders}\n\n"
        "## Mods\n\n"
        f"{mods}\n\n"
        "## Suspicious Or Unsupported Files\n\n"
        "Suspicious:\n"
        f"{suspicious}\n\n"
        "Unsupported/unreadable:\n"
        f"{unsupported}\n\n"
        "## Recommendation\n\n"
        f"{recommendations}\n\n"
        "## Optional Extract Result\n\n"
        "Copied:\n"
        f"{copied}\n\n"
        "Skipped existing files:\n"
        f"{skipped}\n\n"
        "## Questions For Client\n\n"
        "- What exact Minecraft version is this pack for?\n"
        "- What loader is required: Fabric, Forge, NeoForge, or vanilla?\n"
        "- Is Fabric API required for this pack?\n"
    )


def render_mod_line(mod: ModInfo) -> str:
    markers = ", ".join(sorted(mod.loader_markers)) or "unknown"
    versions = ", ".join(sorted(mod.minecraft_versions, key=version_sort_key)) or "unknown"
    ids = ", ".join(sorted(mod.mod_ids)) or "unknown"
    note = f"; {mod.note}" if mod.note else ""
    return f"- `{mod.path}` | loader: {markers} | mod id: {ids} | mc: {versions}{note}"


def write_report(path: Path, report: InspectionReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(report), encoding="utf-8")


def inspect_archive(
    archive_path: Path,
    *,
    output_path: Path = DEFAULT_REPORT_PATH,
    extract_to: Path | None = None,
    clean: bool = False,
    rar_candidates: list[Path] | None = None,
) -> InspectionReport:
    archive_path = archive_path.resolve()
    if not archive_path.is_file():
        report = InspectionReport(archive=archive_path, status="failed", error="Archive file does not exist.")
        write_report(output_path, report)
        raise ClientPackInspectionError(report.error)

    with tempfile.TemporaryDirectory(prefix="mslaunch-pack-") as temp_dir:
        temp_root = Path(temp_dir)
        try:
            extract_archive(archive_path, temp_root, rar_candidates)
            report, sources = analyze_client_pack(archive_path, temp_root)
            if extract_to is not None:
                copy_sources_to_server_pack(sources, extract_to, clean=clean, report=report)
        except ClientPackInspectionError as exc:
            report = InspectionReport(archive=archive_path, status="failed", error=str(exc))
            report.recommendations.append(str(exc))
            write_report(output_path, report)
            raise

        write_report(output_path, report)
        return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely inspect a client Minecraft modpack archive.")
    parser.add_argument("--archive", required=True, help="Path to .zip or .rar archive.")
    parser.add_argument("--output", default=str(DEFAULT_REPORT_PATH), help="Markdown report path.")
    parser.add_argument("--extract-to", default="", help="Optional server_pack target folder.")
    parser.add_argument("--clean", action="store_true", help="Clean only mods/config/resourcepacks inside --extract-to before copying.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    extract_to = Path(args.extract_to) if args.extract_to else None
    try:
        report = inspect_archive(
            Path(args.archive),
            output_path=output_path,
            extract_to=extract_to,
            clean=args.clean,
        )
    except ClientPackInspectionError as exc:
        print(f"Client pack inspection failed: {exc}", file=sys.stderr)
        print(f"Report written to: {output_path}", file=sys.stderr)
        return 2

    print(f"Client pack inspection: {report.status}")
    print(f"loader={report.loader_guess} confidence={report.confidence} mods={report.mod_count}")
    print(f"Report written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
