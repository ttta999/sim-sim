import { api } from "./api.js";
import { refresh } from "./cards.js";

const modal = document.getElementById("modal");
const form = document.getElementById("card-form");
const titleEl = document.getElementById("modal-title");

function hapticNotify(kind = "success") {
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred(kind);
}
function hapticImpact() {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred("light");
}

export function openForm(card = null) {
    hapticImpact();
    form.reset();
    document.getElementById("card-id").value = card ? card.id : "";
    titleEl.textContent = card ? "Редактировать карту" : "Добавить карту";
    if (card) {
        document.getElementById("phone").value = card.phone_number;
        document.getElementById("balance").value = card.balance;
        const days = Math.max(0, Math.ceil((new Date(card.next_payment_date) - new Date()) / 86400000));
        document.getElementById("days").value = days;
        document.getElementById("note").value = card.note || "";
    }
    modal.classList.remove("hidden");
}

export function closeForm() {
    modal.classList.add("hidden");
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("card-id").value;
    const days = parseInt(document.getElementById("days").value, 10);
    const nextDate = new Date();
    nextDate.setDate(nextDate.getDate() + days);
    const payload = {
        phone_number: document.getElementById("phone").value.trim(),
        balance: parseFloat(document.getElementById("balance").value),
        next_payment_date: nextDate.toISOString().slice(0, 10),
        note: document.getElementById("note").value.trim(),
    };
    try {
        if (id) await api.updateCard(id, payload);
        else await api.createCard(payload);
        hapticNotify("success");
        closeForm();
        await refresh();
    } catch (err) {
        hapticNotify("error");
        alert("Ошибка: " + err.message);
    }
});

document.getElementById("cancel-btn").onclick = closeForm;
modal.addEventListener("click", (e) => { if (e.target === modal) closeForm(); });