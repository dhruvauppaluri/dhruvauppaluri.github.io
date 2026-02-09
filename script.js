const routes = {
  "nav-home": "index.html",
  "nav-about": "about.html",
  "nav-projects": "projects.html",
  "nav-resume": "resume.html",
};

const labels = {
  "nav-home": "Home (VIN / TP0)",
  "nav-about": "U1 → About",
  "nav-projects": "R1 → Projects",
  "nav-resume": "TP1 → Resume",
};

const tooltip = document.getElementById("tooltip");

function go(id){
  const dest = routes[id];
  if (!dest) return;
  window.location.href = dest;
}

function showTip(evt, id){
  if (!tooltip) return;
  tooltip.textContent = labels[id] || "Open";
  tooltip.style.left = `${evt.clientX}px`;
  tooltip.style.top = `${evt.clientY + window.scrollY}px`;
  tooltip.style.display = "block";
  tooltip.setAttribute("aria-hidden", "false");
}

function hideTip(){
  if (!tooltip) return;
  tooltip.style.display = "none";
  tooltip.setAttribute("aria-hidden", "true");
}

document.querySelectorAll(".node").forEach(el => {
  const id = el.id;

  el.addEventListener("click", () => go(id));

  el.addEventListener("mousemove", (e) => showTip(e, id));
  el.addEventListener("mouseleave", hideTip);

  el.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      go(id);
    }
  });
});
