const consoleOutput = document.querySelector("[data-console-output]");
const timeline = document.querySelector("[data-timeline]");
const healthIndicator = document.querySelector("[data-health-indicator]");
const healthDetail = document.querySelector("[data-health-detail]");
const lastAction = document.querySelector("[data-last-action]");
const quickWalletHint = document.querySelector("[data-wallet-hint]");
const clearConsoleButton = document.querySelector("[data-clear-console]");
const healthButton = document.querySelector("[data-health-refresh]");

const responseSlots = Object.fromEntries(
    Array.from(document.querySelectorAll("[data-response]")).map((element) => [
        element.dataset.response,
        element,
    ])
);

const state = {
    history: [],
    latestWalletId: null,
    latestUserId: null,
};

function randomIdempotencyKey() {
    if (window.crypto?.randomUUID) {
        return window.crypto.randomUUID();
    }

    return `demo-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatJson(value) {
    return JSON.stringify(value, null, 2);
}

function setConsole(title, payload) {
    if (!consoleOutput) {
        return;
    }

    consoleOutput.textContent = `${title}\n\n${formatJson(payload)}`;
}

function setResponse(slot, payload) {
    const target = responseSlots[slot];
    if (!target) {
        return;
    }

    target.textContent = formatJson(payload);
}

function renderTimeline() {
    if (!timeline) {
        return;
    }

    if (!state.history.length) {
        timeline.innerHTML =
            '<p class="console-empty">No actions yet. Use one of the forms to start talking to the API.</p>';
        return;
    }

    timeline.innerHTML = state.history
        .slice(0, 6)
        .map(
            (entry) => `
                <article class="timeline-item">
                    <strong>${entry.title}</strong>
                    <p>${entry.summary}</p>
                    <time>${entry.time}</time>
                </article>
            `
        )
        .join("");
}

function pushHistory(title, summary) {
    const timestamp = new Date();
    state.history.unshift({
        title,
        summary,
        time: timestamp.toLocaleTimeString(),
    });

    if (lastAction) {
        lastAction.textContent = `${title} at ${timestamp.toLocaleTimeString()}`;
    }

    renderTimeline();
}

function rememberEntities(payload) {
    if (payload?.id && payload?.wallet?.id) {
        state.latestUserId = payload.id;
        state.latestWalletId = payload.wallet.id;
    } else if (payload?.id && payload?.user_id) {
        state.latestWalletId = payload.id;
        state.latestUserId = payload.user_id;
    }

    if (state.latestWalletId && quickWalletHint) {
        quickWalletHint.textContent = `Latest wallet in focus: #${state.latestWalletId}`;
    }
}

async function callApi({ method = "GET", path, headers = {} }) {
    const response = await fetch(path, {
        method,
        headers,
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        throw {
            status: response.status,
            payload,
        };
    }

    return payload;
}

async function refreshHealth() {
    if (!healthIndicator || !healthDetail) {
        return;
    }

    try {
        const payload = await callApi({ path: "/health" });
        healthIndicator.textContent = "API online";
        healthIndicator.classList.add("is-online");
        healthDetail.textContent = `Health check passed with status: ${payload.status}`;
    } catch (error) {
        healthIndicator.textContent = "API unreachable";
        healthIndicator.classList.remove("is-online");
        healthDetail.textContent = `Health check failed${error.status ? ` (${error.status})` : ""}.`;
    }
}

const createUserForm = document.querySelector("[data-form='create-user']");
if (createUserForm) {
    createUserForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        try {
            const payload = await callApi({ method: "POST", path: "/users" });
            setResponse("create-user", payload);
            setConsole("POST /users", payload);
            rememberEntities(payload);
            pushHistory("User created", `User #${payload.id} was created with an initial wallet.`);
        } catch (error) {
            setResponse("create-user", error.payload);
            setConsole("POST /users failed", error.payload);
            pushHistory("Create user failed", `Request returned ${error.status || "an error"}.`);
        }
    });
}

const getUserForm = document.querySelector("[data-form='get-user']");
if (getUserForm) {
    getUserForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const userId = form.elements.user_id.value.trim();

        try {
            const payload = await callApi({ path: `/users/${userId}` });
            setResponse("get-user", payload);
            setConsole(`GET /users/${userId}`, payload);
            rememberEntities(payload);
            pushHistory(
                "User fetched",
                `Loaded user #${payload.id} with wallet #${payload.wallet.id}.`
            );
        } catch (error) {
            setResponse("get-user", error.payload);
            setConsole(`GET /users/${userId} failed`, error.payload);
            pushHistory("User lookup failed", `User #${userId} returned ${error.status || "an error"}.`);
        }
    });
}

const getWalletForm = document.querySelector("[data-form='get-wallet']");
if (getWalletForm) {
    getWalletForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const walletId = form.elements.wallet_id.value.trim();

        try {
            const payload = await callApi({ path: `/wallets/${walletId}` });
            setResponse("get-wallet", payload);
            setConsole(`GET /wallets/${walletId}`, payload);
            rememberEntities(payload);
            pushHistory("Wallet fetched", `Wallet #${payload.id} balance is ${payload.balance}.`);
        } catch (error) {
            setResponse("get-wallet", error.payload);
            setConsole(`GET /wallets/${walletId} failed`, error.payload);
            pushHistory(
                "Wallet lookup failed",
                `Wallet #${walletId} returned ${error.status || "an error"}.`
            );
        }
    });
}

const transferForm = document.querySelector("[data-form='transfer']");
if (transferForm) {
    transferForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const fromWalletId = form.elements.from_wallet_id.value.trim();
        const toWalletId = form.elements.to_wallet_id.value.trim();
        const amount = form.elements.amount.value.trim();
        const idempotencyKey =
            form.elements.idempotency_key.value.trim() || randomIdempotencyKey();

        form.elements.idempotency_key.value = idempotencyKey;

        const params = new URLSearchParams({
            from_wallet_id: fromWalletId,
            to_wallet_id: toWalletId,
            amount,
        });

        try {
            const payload = await callApi({
                method: "POST",
                path: `/transfers?${params.toString()}`,
                headers: {
                    "Idempotency-Key": idempotencyKey,
                },
            });
            setResponse("transfer", payload);
            setConsole("POST /transfers", payload);
            pushHistory(
                "Transfer created",
                `Moved ${payload.amount} from wallet #${payload.from_wallet_id} to wallet #${payload.to_wallet_id}.`
            );
        } catch (error) {
            setResponse("transfer", error.payload);
            setConsole("POST /transfers failed", error.payload);
            pushHistory("Transfer failed", `Transfer request returned ${error.status || "an error"}.`);
        }
    });

    const idempotencyInput = transferForm.querySelector("[name='idempotency_key']");
    if (idempotencyInput) {
        idempotencyInput.value = randomIdempotencyKey();
    }
}

if (clearConsoleButton) {
    clearConsoleButton.addEventListener("click", () => {
        if (consoleOutput) {
            consoleOutput.textContent =
                "Console cleared.\n\nRun an action to inspect the next API response.";
        }
    });
}

if (healthButton) {
    healthButton.addEventListener("click", refreshHealth);
}

renderTimeline();
refreshHealth();
