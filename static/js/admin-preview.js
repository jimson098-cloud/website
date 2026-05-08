(() => {
    const button = document.getElementById("preview-footer-btn");
    if (!button) return;

    const value = (id) => {
        const element = document.getElementById(id);
        return element ? element.value.trim() : "";
    };

    button.addEventListener("click", () => {
        document.getElementById("preview-about").textContent = value("footer_about") || "-";
        document.getElementById("preview-email").textContent = value("footer_email") || "-";
        document.getElementById("preview-phone").textContent = value("footer_phone") || "-";

        const socialItems = [];
        if (value("social_instagram_url")) socialItems.push("Instagram");
        if (value("social_facebook_url")) socialItems.push("Facebook");
        if (value("social_tiktok_url")) socialItems.push("TikTok");
        if (value("social_linkedin_url")) socialItems.push("LinkedIn");
        document.getElementById("preview-social").textContent = socialItems.length ? socialItems.join(", ") : "-";

        const extraLinks = [];
        const l1 = value("footer_link_1_label");
        const l2 = value("footer_link_2_label");
        const l3 = value("footer_link_3_label");
        if (l1) extraLinks.push(l1);
        if (l2) extraLinks.push(l2);
        if (l3) extraLinks.push(l3);
        document.getElementById("preview-links").textContent = extraLinks.length ? extraLinks.join(", ") : "-";
    });
})();
