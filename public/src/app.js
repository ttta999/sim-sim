import { api } from "./api.js";
import { refresh } from "./cards.js";
import { openForm } from "./form.js";

// Инициализация Telegram WebApp
if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
    window.Telegram.WebApp.setHeaderColor("bg_color");

    // MainButton — «Добавить номер»
    const mb = window.Telegram.WebApp.MainButton;
    mb.setText("➕ Добавить номер");
    mb.show();
    mb.onClick(() => openForm());
}

refresh();