import { useEffect, useRef } from "react";

const MOBILE_QUERY = "(max-width: 639px)";
const THRESHOLD_RATIO = 0.35;
const EDGE_GUARD_PX = 20;
const LOCK_ANGLE_TAN = 0.58;

type SwipeAction = { path: string; label: string };

function rightAction(view: string): SwipeAction | null {
  if (view === "archived") return { path: "unarchive", label: "unarchive" };
  if (view === "trash") return { path: "restore", label: "restore" };
  if (view === "trend") return null;
  return { path: "archive", label: "archive" };
}

function leftAction(view: string): SwipeAction | null {
  if (view === "trash") return null;
  return { path: "delete", label: "delete" };
}

export function useSwipeRow(
  articleId: string,
  view: string,
  onArchive: () => void,
  onUnarchive: () => void,
  onRestore: () => void,
  onDelete: () => void,
) {
  const rowRef = useRef<HTMLLIElement | null>(null);

  useEffect(() => {
    const row = rowRef.current;
    if (!row) return;

    const surface = row.querySelector<HTMLElement>(".swipe-surface");
    if (!surface) return;

    const leftBg = row.querySelector<HTMLElement>(".swipe-bg-left");
    const rightBg = row.querySelector<HTMLElement>(".swipe-bg-right");

    const setTransform = (dx: number) => {
      surface.style.transform = `translateX(${dx}px)`;
    };

    const setBgOpacity = (dx: number, width: number) => {
      const ratio = Math.min(1, Math.abs(dx) / (width * THRESHOLD_RATIO));
      if (leftBg) leftBg.style.opacity = dx < 0 ? String(ratio) : "0";
      if (rightBg) rightBg.style.opacity = dx > 0 ? String(ratio) : "0";
    };

    const resetRow = () => {
      surface.style.transition = "transform 180ms ease-out";
      setTransform(0);
      if (leftBg) leftBg.style.opacity = "0";
      if (rightBg) rightBg.style.opacity = "0";
      const clear = () => {
        surface.style.transition = "";
        surface.removeEventListener("transitionend", clear);
      };
      surface.addEventListener("transitionend", clear);
    };

    const commitSwipe = (direction: -1 | 1, action: SwipeAction) => {
      const width = row.offsetWidth;
      const target = direction * width * 1.05;
      surface.style.transition = "transform 160ms ease-out";
      setTransform(target);
      window.setTimeout(() => {
        if (action.path === "delete") void onDelete();
        else if (action.path === "archive") void onArchive();
        else if (action.path === "unarchive") void onUnarchive();
        else if (action.path === "restore") void onRestore();
      }, 160);
    };

    let startX = 0;
    let startY = 0;
    let dx = 0;
    let dy = 0;
    let tracking = false;
    let locked: "scroll" | "swipe" | null = null;
    let pointerId: number | null = null;

    const onDown = (ev: PointerEvent) => {
      if (!window.matchMedia(MOBILE_QUERY).matches) return;
      if (ev.pointerType === "mouse") return;
      if ((ev.target as HTMLElement).closest("a,button,input,textarea,label,select")) return;
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

    const onMove = (ev: PointerEvent) => {
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
        try {
          surface.setPointerCapture(ev.pointerId);
        } catch {
          /* ignore */
        }
      }
      if (locked !== "swipe") return;
      ev.preventDefault();
      const la = leftAction(view);
      const ra = rightAction(view);
      if (dx < 0 && !la) dx = Math.max(dx / 4, -30);
      if (dx > 0 && !ra) dx = Math.min(dx / 4, 30);
      setTransform(dx);
      setBgOpacity(dx, row.offsetWidth);
    };

    const onUp = (ev: PointerEvent) => {
      if (!tracking && locked !== "swipe") return;
      if (ev.pointerId !== pointerId) return;
      tracking = false;
      const wasSwipe = locked === "swipe";
      locked = null;
      try {
        if (pointerId !== null) surface.releasePointerCapture(pointerId);
      } catch {
        /* ignore */
      }
      pointerId = null;
      if (!wasSwipe) return;
      const width = row.offsetWidth;
      const threshold = width * THRESHOLD_RATIO;
      const la = leftAction(view);
      const ra = rightAction(view);
      if (dx <= -threshold) {
        if (la) {
          commitSwipe(-1, la);
          return;
        }
      } else if (dx >= threshold) {
        if (ra) {
          commitSwipe(1, ra);
          return;
        }
      }
      resetRow();
    };

    surface.addEventListener("pointerdown", onDown);
    surface.addEventListener("pointermove", onMove);
    surface.addEventListener("pointerup", onUp);
    surface.addEventListener("pointercancel", onUp);

    return () => {
      surface.removeEventListener("pointerdown", onDown);
      surface.removeEventListener("pointermove", onMove);
      surface.removeEventListener("pointerup", onUp);
      surface.removeEventListener("pointercancel", onUp);
    };
  }, [articleId, view, onArchive, onUnarchive, onRestore, onDelete]);

  return rowRef;
}
