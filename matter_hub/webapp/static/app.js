window.matterHub = {
  initSystemTheme() {
    if (this.systemThemeBound) return;
    this.systemThemeBound = true;
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const root = document.documentElement;
    const applySystemTheme = (isDark) => {
      root.classList.toggle("dark", isDark);
      root.style.colorScheme = isDark ? "dark" : "light";
    };
    applySystemTheme(mediaQuery.matches);
    mediaQuery.addEventListener("change", (ev) => applySystemTheme(ev.matches));
  },
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

// Mobile swipe gestures for article rows.
(function () {
  const MOBILE_QUERY = "(max-width: 639px)";
  const THRESHOLD_RATIO = 0.35;
  const EDGE_GUARD_PX = 20;
  const LOCK_ANGLE_TAN = 0.58;

  function rightAction(view) {
    if (view === "archived") return { url: "unarchive", label: "unarchive" };
    if (view === "trash") return { url: "restore", label: "restore" };
    if (view === "trend") return null;
    return { url: "archive", label: "archive" };
  }

  function leftAction(view) {
    if (view === "trash") return null;
    return { url: "delete", label: "delete" };
  }

  function setTransform(surface, dx) {
    surface.style.transform = `translateX(${dx}px)`;
  }

  function setBgOpacity(row, dx, width) {
    const left = row.querySelector(".swipe-bg-left");
    const right = row.querySelector(".swipe-bg-right");
    const ratio = Math.min(1, Math.abs(dx) / (width * THRESHOLD_RATIO));
    if (left) left.style.opacity = dx < 0 ? String(ratio) : "0";
    if (right) right.style.opacity = dx > 0 ? String(ratio) : "0";
  }

  function resetRow(row, surface) {
    surface.style.transition = "transform 180ms ease-out";
    setTransform(surface, 0);
    const left = row.querySelector(".swipe-bg-left");
    const right = row.querySelector(".swipe-bg-right");
    if (left) left.style.opacity = "0";
    if (right) right.style.opacity = "0";
    const clear = () => {
      surface.style.transition = "";
      surface.removeEventListener("transitionend", clear);
    };
    surface.addEventListener("transitionend", clear);
  }

  function commitSwipe(row, surface, direction, action) {
    const width = row.offsetWidth;
    const target = direction * width * 1.05;
    surface.style.transition = "transform 160ms ease-out";
    setTransform(surface, target);
    const articleId = row.dataset.articleId;
    const url = `/articles/${articleId}/${action.url}`;
    const doRequest = () => {
      if (window.htmx && typeof window.htmx.ajax === "function") {
        window.htmx.ajax("POST", url, {
          target: `#row-${articleId}`,
          swap: "outerHTML",
        });
      } else {
        fetch(url, { method: "POST" }).then(() => {
          if (row.parentNode) row.parentNode.removeChild(row);
        });
      }
    };
    setTimeout(doRequest, 160);
  }

  function attachSwipe(row) {
    if (row.dataset.swipeBound === "1") return;
    row.dataset.swipeBound = "1";
    const surface = row.querySelector(".swipe-surface");
    if (!surface) return;

    let startX = 0;
    let startY = 0;
    let dx = 0;
    let dy = 0;
    let tracking = false;
    let locked = null;
    let pointerId = null;

    const onDown = (ev) => {
      if (!window.matchMedia(MOBILE_QUERY).matches) return;
      if (ev.pointerType === "mouse") return;
      if (ev.target.closest("a,button,input,textarea,label,select")) return;
      if (ev.clientX < EDGE_GUARD_PX) return;
      tracking = true;
      locked = null;
      pointerId = ev.pointerId;
      startX = ev.clientX;
      startY = ev.clientY;
      dx = 0;
      dy = 0;
      surface.style.transition = "";
    };

    const onMove = (ev) => {
      if (!tracking || ev.pointerId !== pointerId) return;
      dx = ev.clientX - startX;
      dy = ev.clientY - startY;
      if (locked === null) {
        if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
        if (Math.abs(dy) > Math.abs(dx) * LOCK_ANGLE_TAN) {
          locked = "scroll";
          tracking = false;
          return;
        }
        locked = "swipe";
        try { surface.setPointerCapture(pointerId); } catch (_e) {}
      }
      if (locked !== "swipe") return;
      ev.preventDefault();
      const view = row.dataset.view;
      if (dx < 0 && !leftAction(view)) dx = Math.max(dx / 4, -30);
      if (dx > 0 && !rightAction(view)) dx = Math.min(dx / 4, 30);
      setTransform(surface, dx);
      setBgOpacity(row, dx, row.offsetWidth);
    };

    const onUp = (ev) => {
      if (!tracking && locked !== "swipe") return;
      if (ev.pointerId !== pointerId) return;
      tracking = false;
      const wasSwipe = locked === "swipe";
      locked = null;
      try { surface.releasePointerCapture(pointerId); } catch (_e) {}
      pointerId = null;
      if (!wasSwipe) return;
      const width = row.offsetWidth;
      const threshold = width * THRESHOLD_RATIO;
      const view = row.dataset.view;
      if (dx <= -threshold) {
        const act = leftAction(view);
        if (act) { commitSwipe(row, surface, -1, act); return; }
      } else if (dx >= threshold) {
        const act = rightAction(view);
        if (act) { commitSwipe(row, surface, 1, act); return; }
      }
      resetRow(row, surface);
    };

    surface.addEventListener("pointerdown", onDown);
    surface.addEventListener("pointermove", onMove);
    surface.addEventListener("pointerup", onUp);
    surface.addEventListener("pointercancel", onUp);
  }

  function bindAll(root) {
    const scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll(".article-row").forEach(attachSwipe);
  }

  document.addEventListener("DOMContentLoaded", () => {
    window.matterHub.initSystemTheme();
    bindAll(document);
  });
  document.body.addEventListener("htmx:afterSwap", (ev) => {
    bindAll(ev.target);
  });
})();
