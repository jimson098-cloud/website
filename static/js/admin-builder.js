(() => {
    const dataTag = document.getElementById("page-blocks-data");
    const hiddenInput = document.getElementById("page_blocks_json");
    const pageSelect = document.getElementById("builder-page-select");
    const blockTypeSelect = document.getElementById("builder-block-type");
    const addBlockButton = document.getElementById("builder-add-block");
    const list = document.getElementById("builder-list");
    const form = document.getElementById("content-form");

    if (!dataTag || !hiddenInput || !pageSelect || !blockTypeSelect || !addBlockButton || !list || !form) {
        return;
    }

    const pages = ["home", "diensten", "portfolio", "over_ons", "contact"];
    let dragIndex = -1;

    const defaultState = { home: [], diensten: [], portfolio: [], over_ons: [], contact: [] };
    let state = defaultState;

    try {
        const parsed = JSON.parse(dataTag.textContent || "{}");
        state = { ...defaultState, ...parsed };
    } catch (_) {
        state = defaultState;
    }

    function serialize() {
        hiddenInput.value = JSON.stringify(state);
    }

    function currentPage() {
        return pageSelect.value;
    }

    function currentBlocks() {
        const page = currentPage();
        if (!Array.isArray(state[page])) {
            state[page] = [];
        }
        return state[page];
    }

    function blockCard(block, index) {
        const card = document.createElement("div");
        card.className = "builder-item";
        card.draggable = true;
        card.dataset.index = String(index);

        card.innerHTML = `
            <div class="builder-item-head">
                <strong>${index + 1}. ${block.type.toUpperCase()}</strong>
                <button type="button" class="btn btn-secondary builder-remove">Verwijder</button>
            </div>
            <label>Titel</label>
            <input type="text" class="builder-field" data-field="title" value="${(block.title || "").replace(/"/g, "&quot;")}">
            <label>Tekst</label>
            <textarea class="builder-field" data-field="text" rows="3">${block.text || ""}</textarea>
            <label>Afbeelding URL</label>
            <input type="url" class="builder-field" data-field="image_url" value="${(block.image_url || "").replace(/"/g, "&quot;")}">
            <label>Knop label</label>
            <input type="text" class="builder-field" data-field="button_label" value="${(block.button_label || "").replace(/"/g, "&quot;")}">
            <label>Knop URL</label>
            <input type="url" class="builder-field" data-field="button_url" value="${(block.button_url || "").replace(/"/g, "&quot;")}">
        `;

        card.addEventListener("dragstart", () => {
            dragIndex = index;
        });
        card.addEventListener("dragover", (event) => event.preventDefault());
        card.addEventListener("drop", (event) => {
            event.preventDefault();
            const dropIndex = index;
            if (dragIndex === -1 || dragIndex === dropIndex) return;
            const blocks = currentBlocks();
            const moved = blocks.splice(dragIndex, 1)[0];
            blocks.splice(dropIndex, 0, moved);
            dragIndex = -1;
            render();
        });

        card.querySelector(".builder-remove").addEventListener("click", () => {
            const blocks = currentBlocks();
            blocks.splice(index, 1);
            render();
        });

        card.querySelectorAll(".builder-field").forEach((field) => {
            field.addEventListener("input", () => {
                const blocks = currentBlocks();
                const blockRef = blocks[index];
                blockRef[field.dataset.field] = field.value;
                serialize();
            });
        });

        return card;
    }

    function render() {
        const blocks = currentBlocks();
        list.innerHTML = "";
        blocks.forEach((block, index) => {
            list.appendChild(blockCard(block, index));
        });
        serialize();
    }

    addBlockButton.addEventListener("click", () => {
        const type = blockTypeSelect.value;
        currentBlocks().push({
            type,
            title: "",
            text: "",
            image_url: "",
            button_label: "",
            button_url: "",
        });
        render();
    });

    pageSelect.addEventListener("change", render);
    form.addEventListener("submit", serialize);

    pages.forEach((page) => {
        if (!Array.isArray(state[page])) state[page] = [];
    });

    render();
})();
