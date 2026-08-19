import { api } from "./api.js";
import { openForm } from "./form.js";

const listEl = document.getElementById("cards-list");
const emptyEl = document.getElementById("empty-state");
const loadingEl = document.getElementById("loading");

function haptic(type = "light") {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred(type);
}
function hapticNotify(kind = "success") {
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred(kind);
}

function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString("lv-LV", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatBalance(v) {
    return new Intl.NumberFormat("lv-LV", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v);
}

function daysToPayment(iso) {
    const target = new Date(iso);
    const today = new Date();
    target.setHours(0, 0, 0, 0);
    today.setHours(0, 0, 0, 0);
    return Math.ceil((target - today) / (1000 * 60 * 60 * 24));
}

function daysBadge(days) {
    let cls, label;
    if (days < 0) { cls = "days-red"; label = `просрочено на ${Math.abs(days)} дн.`; }
    else if (days === 0) { cls = "days-red"; label = "сегодня"; }
    else if (days <= 3) { cls = "days-red"; label = `${days} дн.`; }
    else if (days <= 7) { cls = "days-yellow"; label = `${days} дн.`; }
    else { cls = "days-green"; label = `${days} дн.`; }
    return `<span class="days-badge ${cls}">⏳ ${label}</span>`;
}

function renderCard(card) {
    const days = daysToPayment(card.next_payment_date);
    const div = document.createElement("div");
    div.className = "card";
    div.innerHTML = `
        <div class="flex justify-between items-start mb-2">
            <div class="font-bold text-lg">${card.phone_number}</div>
            ${daysBadge(days)}
        </div>
        <div class="flex justify-between text-sm opacity-80 mb-2">
            <span>💰 ${formatBalance(card.balance)} €</span>
            <span>до ${formatDate(card.next_payment_date)}</span>
        </div>
        ${card.note ? `<div class="text-sm opacity-70 mb-3 italic">📝 ${escapeHtml(card.note)}</div>` : ""}
        <div class="flex gap-2 pt-1 border-t border-[var(--tg-theme-hint-color)]/20">
            <button class="flex-1 text-sm py-1.5 rounded bg-[var(--tg-theme-button-color)] text-[var(--tg-theme-button-text-color)] edit-btn">✏️ Редактировать</button>
            <button class="flex-1 text-sm py-1.5 rounded bg-red-500/20 text-red-500 del-btn">🗑 Удалить</button>
        </div>
    `;
    div.querySelector(".edit-btn").onclick = () => openForm(card);
    div.querySelector(".del-btn").onclick = () => deleteCard(card);
    return div;
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function deleteCard(card) {
    window.Telegram?.WebApp?.showConfirm?.("Удалить эту карту?", async (ok) => {
        if (!ok) return;
        try {
            haptic("medium");
            await api.deleteCard(card.id);
            hapticNotify("success");
            await refresh();
        } catch (e) {
            alert("Ошибка удаления: " + e.message);
        }
    });
}

export async function refresh() {
    loadingEl.classList.remove("hidden");
    listEl.innerHTML = "";
    try {
        const cards = await api.listCards();
        loadingEl.classList.add("hidden");
        if (cards.length === 0) {
            emptyEl.classList.remove("hidden");
            return;
        }
        emptyEl.classList.add("hidden");
        // Сортировка: сначала самые срочные
        cards.sort((a, b) => daysToPayment(a.next_payment_date) - daysToPayment(b.next_payment_date));
        cards.forEach(c => listEl.appendChild(renderCard(c)));
    } catch (e) {
        loadingEl.classList.add("hidden");
        listEl.innerHTML = `<div class="text-red-500 text-center py-8">Ошибка: ${e.message}</div>`;
    }
}