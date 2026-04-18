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
};
