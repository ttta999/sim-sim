const API_BASE = import.meta.env?.VITE_API_URL ?? window.location.origin;

function getInitData() {
    return window.Telegram?.WebApp?.initData || "";
}

async function request(method, path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method,
        headers: {
            "Content-Type": "application/json",
            "X-Telegram-Init-Data": getInitData(),
        },
        body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 204) return null;
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Ошибка ${res.status}`);
    }
    return res.json();
}

export const api = {
    listCards: () => request("GET", "/api/cards"),
    createCard: (data) => request("POST", "/api/cards", data),
    updateCard: (id, data) => request("PUT", `/api/cards/${id}`, data),
    deleteCard: (id) => request("DELETE", `/api/cards/${id}`),
};