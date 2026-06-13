from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget


def prompt_report_message(
    parent: QWidget,
    *,
    title: str,
    body: str,
    placeholder: str,
    accept_label: str,
    cancel_label: str,
    stylesheet: str,
    empty_message: str,
    on_empty: Callable[[str], None],
) -> str | None:
    dialog = QDialog(parent)
    dialog.setObjectName("accessDialog")
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    dialog.setMinimumWidth(460)
    dialog.setStyleSheet(stylesheet)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)

    title_label = QLabel(title)
    title_label.setObjectName("accessTitle")
    title_label.setWordWrap(True)

    body_label = QLabel(body)
    body_label.setObjectName("accessBody")
    body_label.setWordWrap(True)

    message_input = QPlainTextEdit()
    message_input.setObjectName("reportTextInput")
    message_input.setPlaceholderText(placeholder)
    message_input.setMinimumHeight(150)

    buttons = QHBoxLayout()
    buttons.addStretch(1)

    cancel_button = QPushButton(cancel_label)
    send_button = QPushButton(accept_label)
    send_button.setObjectName("primaryDialogButton")
    cancel_button.clicked.connect(dialog.reject)
    send_button.clicked.connect(dialog.accept)
    buttons.addWidget(cancel_button)
    buttons.addWidget(send_button)

    layout.addWidget(title_label)
    layout.addWidget(body_label)
    layout.addWidget(message_input)
    layout.addLayout(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None

    user_message = message_input.toPlainText().strip()
    if not user_message:
        on_empty(empty_message)
        return None
    return user_message[:4000]
