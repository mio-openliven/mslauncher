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
    source_path: Path | None = None

    def to_user_message(self, language: str = "EN") -> str:
        translation = get_crash_translation(self.rule_id, language)
        title = translation.get("title", self.title)
        explanation = translation.get("explanation", self.explanation)
        actions = tuple(translation.get("actions", self.actions))
        labels = get_crash_labels(language)

        parts = [f"{labels['what_happened']}: {title}", explanation]

        if self.mods:
            parts.append(f"{labels['mods']}: {', '.join(self.mods)}")
        if self.mod_ids:
            parts.append(f"{labels['mod_ids']}: {', '.join(self.mod_ids)}")
        if self.dependencies:
            parts.append(f"{labels['dependencies']}: {', '.join(self.dependencies)}")

        if actions:
            parts.append(labels["actions"] + ":\n" + "\n".join(f"- {action}" for action in actions))

        send_lines = [labels["send_log"]]
        if self.source_path is not None:
            send_lines.append(f"{labels['source']}: {self.source_path}")
        parts.append(labels["send_admin"] + ":\n" + "\n".join(f"- {line}" for line in send_lines))

        parts.append(f"{labels['detail']}: {self.detail}")
        return "\n\n".join(parts)


CRASH_TRANSLATIONS: dict[str, dict[str, dict[str, object]]] = {
    "RU": {
        "missing_dependency": {
            "title": "\u041f\u043e\u0445\u043e\u0436\u0435, \u043d\u0435 \u0445\u0432\u0430\u0442\u0430\u0435\u0442 \u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442\u0438 \u0434\u043b\u044f \u043c\u043e\u0434\u0430.",
            "explanation": "\u041e\u0434\u0438\u043d \u0438\u0437 \u043c\u043e\u0434\u043e\u0432 \u0442\u0440\u0435\u0431\u0443\u0435\u0442 \u0434\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u043c\u043e\u0434-\u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0443 \u0438\u043b\u0438 \u0434\u0440\u0443\u0433\u0443\u044e \u0432\u0435\u0440\u0441\u0438\u044e \u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442\u0438.",
            "actions": (
                "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442\u0438 \u0443 \u0443\u043a\u0430\u0437\u0430\u043d\u043d\u043e\u0433\u043e \u043c\u043e\u0434\u0430.",
                "\u0415\u0441\u043b\u0438 \u043d\u0435 \u0445\u0432\u0430\u0442\u0430\u0435\u0442 fabric-api, \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 Fabric API \u043f\u043e\u0434 \u044d\u0442\u0443 \u0432\u0435\u0440\u0441\u0438\u044e Minecraft.",
                "\u0415\u0441\u043b\u0438 \u044d\u0442\u043e \u0441\u0435\u0440\u0432\u0435\u0440\u043d\u0430\u044f \u0441\u0431\u043e\u0440\u043a\u0430, \u043f\u043e\u043f\u0440\u043e\u0441\u0438\u0442\u0435 \u0430\u0434\u043c\u0438\u043d\u0430 \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c manifest \u0438 \u043f\u0435\u0440\u0435\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u0443\u0439\u0442\u0435 \u043f\u0440\u043e\u0444\u0438\u043b\u044c.",
            ),
        },
        "mixin_conflict": {
            "title": "\u041f\u043e\u0445\u043e\u0436\u0435, \u044d\u0442\u043e \u043a\u043e\u043d\u0444\u043b\u0438\u043a\u0442 Mixin \u0438\u043b\u0438 \u043d\u0435\u0432\u0435\u0440\u043d\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f \u043c\u043e\u0434\u0430.",
            "explanation": "Mixin \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f \u043c\u043e\u0434\u0430\u043c\u0438 \u0434\u043b\u044f \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0438\u0433\u0440\u044b. \u041e\u0448\u0438\u0431\u043a\u0430 \u0447\u0430\u0441\u0442\u043e \u0437\u043d\u0430\u0447\u0438\u0442, \u0447\u0442\u043e \u043c\u043e\u0434, loader \u0438\u043b\u0438 \u043f\u0430\u0440\u0430 \u043c\u043e\u0434\u043e\u0432 \u043d\u0435\u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u044b.",
            "actions": (
                "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u0435 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u043d\u044b\u0439 \u043c\u043e\u0434 \u043f\u043e\u0434 \u044d\u0442\u0443 \u0432\u0435\u0440\u0441\u0438\u044e Minecraft \u0438 Fabric/Forge.",
                "\u0415\u0441\u043b\u0438 \u043c\u043e\u0434 \u0434\u043e\u0431\u0430\u0432\u0438\u043b\u0438 \u043d\u0435\u0434\u0430\u0432\u043d\u043e, \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u0443\u0431\u0435\u0440\u0438\u0442\u0435 \u0435\u0433\u043e \u0438 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0437\u0430\u043f\u0443\u0441\u043a.",
                "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435, \u0447\u0442\u043e Fabric API \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u0435\u0442 \u0441 \u0432\u0435\u0442\u043a\u043e\u0439 Minecraft \u0441\u0431\u043e\u0440\u043a\u0438.",
            ),
        },
        "missing_class": {
            "title": "\u041c\u043e\u0434, \u0441\u043a\u043e\u0440\u0435\u0435 \u0432\u0441\u0435\u0433\u043e, \u043d\u0435 \u043f\u043e\u0434\u0445\u043e\u0434\u0438\u0442 \u043f\u043e\u0434 \u044d\u0442\u0443 \u0432\u0435\u0440\u0441\u0438\u044e Minecraft \u0438\u043b\u0438 loader.",
            "explanation": "\u0418\u0433\u0440\u0430 \u043d\u0435 \u043d\u0430\u0448\u043b\u0430 Java-\u043a\u043b\u0430\u0441\u0441 \u0438\u043b\u0438 \u043c\u0435\u0442\u043e\u0434, \u043a\u043e\u0442\u043e\u0440\u044b\u0439 \u0436\u0434\u0430\u043b \u043c\u043e\u0434. \u0427\u0430\u0441\u0442\u043e \u044d\u0442\u043e \u043c\u043e\u0434 \u043e\u0442 \u0434\u0440\u0443\u0433\u043e\u0439 \u0432\u0435\u0440\u0441\u0438\u0438 \u0438\u043b\u0438 \u043d\u0435 \u0445\u0432\u0430\u0442\u0430\u0435\u0442 \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0438.",
            "actions": (
                "\u0421\u043a\u0430\u0447\u0430\u0439\u0442\u0435 \u0432\u0435\u0440\u0441\u0438\u044e \u043c\u043e\u0434\u0430 \u0441\u0442\u0440\u043e\u0433\u043e \u043f\u043e\u0434 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0439 Minecraft.",
                "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 Fabric API, Cloth Config, Architectury, GeckoLib \u0438 \u043f\u043e\u0445\u043e\u0436\u0438\u0435 \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0438.",
                "\u041d\u0435 \u0441\u043c\u0435\u0448\u0438\u0432\u0430\u0439\u0442\u0435 Forge-\u043c\u043e\u0434\u044b \u0441 Fabric-\u0441\u0431\u043e\u0440\u043a\u043e\u0439 \u0438 \u043d\u0430\u043e\u0431\u043e\u0440\u043e\u0442.",
            ),
        },
        "duplicate_mods": {
            "title": "\u0412 \u043f\u0430\u043f\u043a\u0435 mods \u043d\u0430\u0439\u0434\u0435\u043d\u044b \u0434\u0443\u0431\u043b\u0438 \u043c\u043e\u0434\u043e\u0432.",
            "explanation": "Minecraft \u0432\u0438\u0434\u0438\u0442 \u0434\u0432\u0435 \u0432\u0435\u0440\u0441\u0438\u0438 \u043e\u0434\u043d\u043e\u0433\u043e \u0438 \u0442\u043e\u0433\u043e \u0436\u0435 \u043c\u043e\u0434\u0430 \u0438 \u043d\u0435 \u043f\u043e\u043d\u0438\u043c\u0430\u0435\u0442, \u043a\u0430\u043a\u0443\u044e \u0437\u0430\u0433\u0440\u0443\u0436\u0430\u0442\u044c.",
            "actions": (
                "\u041e\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0442\u043e\u043b\u044c\u043a\u043e \u043e\u0434\u043d\u0443 \u0432\u0435\u0440\u0441\u0438\u044e \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u043c\u043e\u0434\u0430.",
                "\u0412 \u0441\u0435\u0440\u0432\u0435\u0440\u043d\u043e\u043c \u043f\u0440\u043e\u0444\u0438\u043b\u0435 \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044e, \u0447\u0442\u043e\u0431\u044b \u043b\u0430\u0443\u043d\u0447\u0435\u0440 \u0443\u0434\u0430\u043b\u0438\u043b \u043b\u0438\u0448\u043d\u0438\u0435 \u043c\u043e\u0434\u044b.",
            ),
        },
        "incompatible_mods": {
            "title": "\u0417\u0430\u0433\u0440\u0443\u0437\u0447\u0438\u043a \u043d\u0430\u0448\u0435\u043b \u043d\u0435\u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u044b\u0435 \u043c\u043e\u0434\u044b.",
            "explanation": "\u041e\u0434\u0438\u043d \u0438\u043b\u0438 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u043c\u043e\u0434\u043e\u0432 \u043d\u0435 \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u044b \u0441 \u0442\u0435\u043a\u0443\u0449\u0435\u0439 \u0432\u0435\u0440\u0441\u0438\u0435\u0439 \u0438\u0433\u0440\u044b, loader \u0438\u043b\u0438 \u0434\u0440\u0443\u0433 \u0441 \u0434\u0440\u0443\u0433\u043e\u043c.",
            "actions": (
                "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0432\u0435\u0440\u0441\u0438\u0438 \u043c\u043e\u0434\u043e\u0432 \u0438 loader.",
                "\u0415\u0441\u043b\u0438 \u043e\u0448\u0438\u0431\u043a\u0430 \u043f\u043e\u044f\u0432\u0438\u043b\u0430\u0441\u044c \u043f\u043e\u0441\u043b\u0435 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0441\u0431\u043e\u0440\u043a\u0438, \u043f\u0435\u0440\u0435\u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u0443\u0439\u0442\u0435 \u0441\u0435\u0440\u0432\u0435\u0440\u043d\u044b\u0439 \u043f\u0440\u043e\u0444\u0438\u043b\u044c.",
                "\u0415\u0441\u043b\u0438 \u044d\u0442\u043e \u043b\u0438\u0447\u043d\u044b\u0435 \u043c\u043e\u0434\u044b, \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u0443\u0431\u0435\u0440\u0438\u0442\u0435 \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043d\u044b\u0435 \u0444\u0430\u0439\u043b\u044b.",
            ),
        },
        "java_version": {
            "title": "\u0412\u044b\u0431\u0440\u0430\u043d\u043d\u0430\u044f Java \u0441\u043b\u0438\u0448\u043a\u043e\u043c \u0441\u0442\u0430\u0440\u0430\u044f \u0434\u043b\u044f \u0438\u0433\u0440\u044b \u0438\u043b\u0438 \u043c\u043e\u0434\u0430.",
            "explanation": "Minecraft \u0438\u043b\u0438 \u043c\u043e\u0434 \u0441\u043e\u0431\u0440\u0430\u043d \u043f\u043e\u0434 \u0431\u043e\u043b\u0435\u0435 \u043d\u043e\u0432\u0443\u044e Java, \u0447\u0435\u043c \u0443\u043a\u0430\u0437\u0430\u043d\u0430 \u0432 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u0445.",
            "actions": (
                "\u0414\u043b\u044f Minecraft 1.20.5+ \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 Java 21.",
                "\u0414\u043b\u044f Minecraft 1.18-1.20.4 \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 Java 17.",
                "\u0412 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u0445 \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430 \u0443\u043a\u0430\u0436\u0438\u0442\u0435 \u0432\u0435\u0440\u043d\u044b\u0439 java.exe.",
            ),
        },
        "out_of_memory": {
            "title": "Minecraft \u043d\u0435 \u0445\u0432\u0430\u0442\u0438\u043b\u043e \u0432\u044b\u0434\u0435\u043b\u0435\u043d\u043d\u043e\u0439 \u043f\u0430\u043c\u044f\u0442\u0438.",
            "explanation": "Java \u0437\u0430\u043a\u043e\u043d\u0447\u0438\u043b\u0430 \u0432\u044b\u0434\u0435\u043b\u0435\u043d\u043d\u0443\u044e RAM \u0432\u043e \u0432\u0440\u0435\u043c\u044f \u0437\u0430\u043f\u0443\u0441\u043a\u0430 \u0438\u043b\u0438 \u0438\u0433\u0440\u044b.",
            "actions": (
                "\u0423\u0432\u0435\u043b\u0438\u0447\u044c\u0442\u0435 Max RAM \u0432 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u0445 \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430.",
                "\u0417\u0430\u043a\u0440\u043e\u0439\u0442\u0435 \u043b\u0438\u0448\u043d\u0438\u0435 \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b \u043f\u0435\u0440\u0435\u0434 \u0437\u0430\u043f\u0443\u0441\u043a\u043e\u043c.",
                "\u0414\u043b\u044f \u0442\u044f\u0436\u0435\u043b\u043e\u0439 \u0441\u0431\u043e\u0440\u043a\u0438 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 4G \u0438\u043b\u0438 6G, \u0435\u0441\u043b\u0438 \u043d\u0430 \u041f\u041a \u0445\u0432\u0430\u0442\u0430\u0435\u0442 \u043f\u0430\u043c\u044f\u0442\u0438.",
            ),
        },
        "unknown": {
            "title": "\u0418\u0433\u0440\u0430 \u043d\u0435\u043e\u0436\u0438\u0434\u0430\u043d\u043d\u043e \u0437\u0430\u043a\u0440\u044b\u043b\u0430\u0441\u044c.",
            "explanation": "\u0422\u043e\u0447\u043d\u0430\u044f \u043f\u0440\u0438\u0447\u0438\u043d\u0430 \u043f\u043e \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u043c \u0441\u0442\u0440\u043e\u043a\u0430\u043c \u043b\u043e\u0433\u0430 \u043d\u0435 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u0430.",
            "actions": (
                "\u041e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u043f\u0430\u043f\u043a\u0443 crash-reports \u0438\u043b\u0438 logs/latest.log.",
                "\u0415\u0441\u043b\u0438 \u043c\u043e\u0434 \u0434\u043e\u0431\u0430\u0432\u0438\u043b\u0438 \u043d\u0435\u0434\u0430\u0432\u043d\u043e, \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u0443\u0431\u0435\u0440\u0438\u0442\u0435 \u0435\u0433\u043e.",
                "\u0415\u0441\u043b\u0438 \u044d\u0442\u043e \u0441\u0435\u0440\u0432\u0435\u0440\u043d\u0430\u044f \u0441\u0431\u043e\u0440\u043a\u0430, \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044e \u043c\u043e\u0434\u043e\u0432 \u0437\u0430\u043d\u043e\u0432\u043e.",
            ),
        },
    }
}


CRASH_LABELS = {
    "EN": {
        "mods": "Possible problem file",
        "mod_ids": "Possible mod id",
        "dependencies": "Possible missing dependency",
        "actions": "What to try",
        "what_happened": "What happened",
        "send_admin": "What to send admin",
        "send_log": "Send latest.log or the newest crash report from crash-reports.",
        "source": "Detected report/log",
        "detail": "Technical line",
    },
    "RU": {
        "mods": "\u0412\u043e\u0437\u043c\u043e\u0436\u043d\u044b\u0439 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u043d\u044b\u0439 \u0444\u0430\u0439\u043b",
        "mod_ids": "\u0412\u043e\u0437\u043c\u043e\u0436\u043d\u044b\u0439 mod id",
        "dependencies": "\u0412\u043e\u0437\u043c\u043e\u0436\u043d\u0430\u044f \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u044e\u0449\u0430\u044f \u0437\u0430\u0432\u0438\u0441\u0438\u043c\u043e\u0441\u0442\u044c",
        "actions": "\u0427\u0442\u043e \u043f\u043e\u043f\u0440\u043e\u0431\u043e\u0432\u0430\u0442\u044c",
        "what_happened": "\u0427\u0442\u043e \u0441\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c",
        "send_admin": "\u0427\u0442\u043e \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0430\u0434\u043c\u0438\u043d\u0443",
        "send_log": "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 latest.log \u0438\u043b\u0438 \u0441\u0430\u043c\u044b\u0439 \u0441\u0432\u0435\u0436\u0438\u0439 crash report \u0438\u0437 crash-reports.",
        "source": "\u041d\u0430\u0439\u0434\u0435\u043d\u043d\u044b\u0439 report/log",
        "detail": "\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430",
    },
}


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


def get_crash_translation(rule_id: str, language: str) -> dict[str, object]:
    language_translations = CRASH_TRANSLATIONS.get(language.upper(), {})
    return language_translations.get(rule_id, {})


def get_crash_labels(language: str) -> dict[str, str]:
    return CRASH_LABELS.get(language.upper(), CRASH_LABELS["EN"])


def advise_crash(
    log_lines: Iterable[str],
    exit_code: int,
    language: str = "EN",
    source_path: str | Path | None = None,
) -> str:
    return analyze_crash(log_lines, exit_code, source_path).to_user_message(language)


def analyze_crash(
    log_lines: Iterable[str],
    exit_code: int,
    source_path: str | Path | None = None,
) -> CrashAdvice:
    lines = list(log_lines)
    lower_log = "\n".join(lines).lower()

    for rule in CRASH_RULES:
        if any(needle in lower_log for needle in rule.needles):
            return build_advice(rule, lines, source_path)

    return CrashAdvice(
        rule_id="unknown",
        title="The game exited unexpectedly.",
        explanation=f"The game exited with code {exit_code}. The exact reason was not recognized.",
        actions=(
            "Open the profile folder and check latest.log or crash-reports.",
            "If a mod was added recently, remove it temporarily.",
            "If this is a server modpack, run mod sync again.",
        ),
        detail="no separate error line found",
        mods=(),
        mod_ids=(),
        dependencies=(),
        source_path=Path(source_path) if source_path else None,
    )


def build_advice(rule: CrashAdviceRule, log_lines: list[str], source_path: str | Path | None = None) -> CrashAdvice:
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
        source_path=Path(source_path) if source_path else None,
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
