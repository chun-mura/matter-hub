window.matterHub = {
  toggleTag(checkbox) {
    const current = new URLSearchParams(window.location.search);
    const tags = new Set((current.get("tags") || "").split(",").filter(Boolean));
    if (checkbox.checked) tags.add(checkbox.value);
    else tags.delete(checkbox.value);
    current.set("tags", Array.from(tags).join(","));
    if (!current.get("view")) current.set("view", "active");
    window.location.search = current.toString();
  },
  toggleTagPanel(btn) {
    const panel = document.getElementById("tag-filter");
    if (!panel) return;
    const open = panel.classList.toggle("hidden") === false;
    btn.setAttribute("aria-expanded", String(open));
    const chev = btn.querySelector(".tag-chevron");
    if (chev) chev.textContent = open ? "▾" : "▸";
  },
};
