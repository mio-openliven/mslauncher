from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CrashAdviceRule:
    rule_id: str
    needles: tuple[str, ...]
    title: str
    explanation: str
    actions: tuple[str, ...]


@dataclass(frozen=True)
class CrashAdvice:
    rule_id: str
    title: str
    explanation: str
    actions: tuple[str, ...]
    detail: str
    mods: tuple[str, ...]
    mod_ids: tuple[str, ...]
    dependencies: tuple[str, ...]

    def to_user_message(self) -> str:
        parts = [self.title, self.explanation]

        if self.mods:
            parts.append(f"Possible problem file: {', '.join(self.mods)}")
        if self.mod_ids:
            parts.append(f"Possible mod id: {', '.join(self.mod_ids)}")
        if self.dependencies:
            parts.append(f"Possible missing dependency: {', '.join(self.dependencies)}")

        if self.actions:
            parts.append("What to try:\n" + "\n".join(f"- {action}" for action in self.actions))

        parts.append(f"Technical line: {self.detail}")
        return "\n\n".join(parts)


CRASH_RULES = (
    CrashAdviceRule(
        rule_id="missing_dependency",
        needles=("missing mandatory dependencies", "requires any version of", "depends on", "requires version"),
        title="A mod dependency seems to be missing.",
        explanation="One of the mods requires an additional library mod or a different dependency version.",
        actions=(
            "Check the dependency list for the mod mentioned above.",
            "If the missing dependency is fabric-api, install Fabric API for this Minecraft version.",
            "If this is a server modpack, ask the admin to update the manifest and re-sync the profile.",
        ),
    ),
    CrashAdviceRule(
        rule_id="mixin_conflict",
        needles=("mixin", "spongepowered", "mixintransformererror", "mixin apply failed", "mixin prepare failed"),
        title="This looks like a Mixin conflict or a wrong mod version.",
        explanation="Mixin is used by mods to patch the game. This error often means a mod, loader, or pair of mods is incompatible.",
        actions=(
            "Update the problem mod to the version matching this Minecraft and Fabric/Forge version.",
            "If a mod was added recently, remove it temporarily and try launching again.",
            "Check that Fabric API matches the same Minecraft branch as the modpack.",
        ),
    ),
    CrashAdviceRule(
        rule_id="missing_class",
        needles=("noclassdeffounderror", "classnotfoundexception", "nosuchmethoderror", "nosuchfielderror"),
        title="A mod likely does not match this Minecraft version or loader.",
        explanation="The game could not find a Java class or method expected by a mod. This often means a wrong mod version or a missing library.",
        actions=(
            "Install the mod version made exactly for the selected Minecraft version.",
            "Check common dependencies such as Fabric API, Cloth Config, Architectury, GeckoLib, and similar libraries.",
            "Do not mix Forge mods into a Fabric modpack, or Fabric mods into a Forge modpack.",
        ),
    ),
    CrashAdviceRule(
        rule_id="duplicate_mods",
        needles=("duplicate mods", "duplicate mod"),
        title="Duplicate mods were found in the mods folder.",
        explanation="Minecraft sees two versions of the same mod and cannot decide which one to load.",
        actions=(
            "Keep only one version of each mod.",
            "In the server profile, run mod sync so the launcher removes extra mods.",
        ),
    ),
    CrashAdviceRule(
        rule_id="incompatible_mods",
        needles=("incompatible mods found", "mod resolution encountered", "modloadingexception", "failed to load mod"),
        title="The loader found incompatible mods.",
        explanation="One or more mods are incompatible with the current game version, loader, or each other.",
        actions=(
            "Check mod and loader versions.",
            "If this started after a modpack update, re-sync the server profile.",
            "If you use personal mods, temporarily remove the most recently added files.",
        ),
    ),
    CrashAdviceRule(
        rule_id="java_version",
        needles=("unsupportedclassversionerror",),
        title="The selected Java version is too old for the game or a mod.",
        explanation="Minecraft or a mod was built for a newer Java version than the one selected in settings.",
        actions=(
            "For Minecraft 1.20.5+, select Java 21.",
            "For Minecraft 1.18-1.20.4, select Java 17.",
            "In launcher settings, point Java path to the correct java.exe.",
        ),
    ),
    CrashAdviceRule(
        rule_id="out_of_memory",
        needles=("outofmemoryerror", "java heap space"),
        title="Minecraft ran out of allocated memory.",
        explanation="Java ran out of memory during startup or gameplay.",
        actions=(
            "Increase Max RAM in launcher settings.",
            "Close unnecessary programs before launching.",
            "For a heavy modpack, try 4G or 6G if the PC has enough memory.",
        ),
    ),
)


def advise_crash(log_lines: Iterable[str], exit_code: int) -> str:
    lines = list(log_lines)
    lower_log = "\n".join(lines).lower()

    for rule in CRASH_RULES:
        if any(needle in lower_log for needle in rule.needles):
            return build_advice(rule, lines).to_user_message()

    return (
        f"The game exited with code {exit_code}. The exact reason was not recognized.\n\n"
        "What to try:\n"
        "- Open the profile folder and check latest.log or crash-reports.\n"
        "- If a mod was added recently, remove it temporarily.\n"
        "- If this is a server modpack, run mod sync again."
    )


def build_advice(rule: CrashAdviceRule, log_lines: list[str]) -> CrashAdvice:
    context = extract_crash_context(log_lines)
    return CrashAdvice(
        rule_id=rule.rule_id,
        title=rule.title,
        explanation=rule.explanation,
        actions=rule.actions,
        detail=extract_relevant_line(log_lines, rule.needles),
        mods=tuple(context["mods"]),
        mod_ids=tuple(context["mod_ids"]),
        dependencies=tuple(context["dependencies"]),
    )


def extract_relevant_line(log_lines: Iterable[str], needles: tuple[str, ...]) -> str:
    for line in reversed(list(log_lines)):
        lower_line = line.lower()
        if any(needle in lower_line for needle in needles):
            return line[-500:]
    return "no separate error line found"


def extract_crash_context(log_lines: Iterable[str]) -> dict[str, list[str]]:
    context = {
        "mods": [],
        "mod_ids": [],
        "dependencies": [],
    }

    for line in reversed(list(log_lines)):
        append_unique(context["mods"], find_mod_files(line), limit=4)
        append_unique(context["mod_ids"], find_mod_ids(line), limit=4)
        append_unique(context["dependencies"], find_dependencies(line), limit=4)

    return context


def find_mod_files(line: str) -> list[str]:
    matches = re.findall(r"[\w.+\-\[\]\(\)/\\]+\.jar", line, flags=re.IGNORECASE)
    return [Path(match.strip()).name for match in matches]


def find_mod_ids(line: str) -> list[str]:
    patterns = [
        r"mod ['\"]([a-z0-9_.-]+)['\"]",
        r"modid[:= ]+['\"]?([a-z0-9_.-]+)",
        r"for mod ([a-z0-9_.-]+)",
        r"failed to load mod ([a-z0-9_.-]+)",
    ]
    found: list[str] = []
    lower_line = line.lower()

    for pattern in patterns:
        found.extend(re.findall(pattern, lower_line, flags=re.IGNORECASE))

    return found


def find_dependencies(line: str) -> list[str]:
    patterns = [
        r"requires (?:any version of|version [^ ]+ of) ['\"]?([a-z0-9_.-]+)",
        r"depends on ['\"]?([a-z0-9_.-]+)",
        r"missing (?:mandatory )?dependencies?:?\s*([a-z0-9_.-]+)",
    ]
    found: list[str] = []
    lower_line = line.lower()

    for pattern in patterns:
        found.extend(re.findall(pattern, lower_line, flags=re.IGNORECASE))

    return found


def append_unique(target: list[str], values: Iterable[str], limit: int) -> None:
    for value in values:
        clean_value = value.strip(" '\".,;:()[]")
        if clean_value and clean_value not in target:
            target.append(clean_value)
        if len(target) >= limit:
            return
