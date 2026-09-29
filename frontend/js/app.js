const { api } = window.CommonApi;

const authSection = document.getElementById("authSection");
const appSection = document.getElementById("appSection");
const authMsg = document.getElementById("authMsg");
const userInfo = document.getElementById("userInfo");

function setAuthMsg(text, tone = "error") {
    authMsg.textContent = text || "";
    authMsg.dataset.tone = tone;
}

function showApp(user) {
    authSection.classList.add("hidden");
    appSection.classList.remove("hidden");
    userInfo.textContent = `${user.username} · ${user.role}`;
}

function showAuth() {
    appSection.classList.add("hidden");
    authSection.classList.remove("hidden");
}

async function refreshSession() {
    const me = await api("/auth/me");
    if (me.ok) {
        showApp(me.body);
        return;
    }
    const refreshed = await api("/auth/refresh", { method: "POST" });
    if (!refreshed.ok) {
        showAuth();
        return;
    }
    const again = await api("/auth/me");
    if (again.ok) {
        showApp(again.body);
    } else {
        showAuth();
    }
}

document.getElementById("loginBtn").addEventListener("click", async () => {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    setAuthMsg("");
    const result = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
    });
    if (result.status === 403 && result.body?.error === "force_password_change") {
        setAuthMsg("Нужна смена пароля (см. /docs → change-password)", "error");
        return;
    }
    if (!result.ok) {
        setAuthMsg(result.body?.message || "Ошибка входа");
        return;
    }
    setAuthMsg("Успешный вход", "ok");
    await refreshSession();
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
    await api("/auth/logout", { method: "POST" });
    showAuth();
    setAuthMsg("Вы вышли", "ok");
});

refreshSession();
