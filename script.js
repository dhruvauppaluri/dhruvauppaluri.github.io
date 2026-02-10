(function () {
  "use strict";

  // Footer year
  var yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  // Mobile menu toggle
  var menuBtn = document.querySelector(".menu-btn");
  var nav = document.querySelector(".nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", nav.classList.contains("open"));
    });

    // Close menu when a link is clicked (smooth scroll target)
    nav.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        nav.classList.remove("open");
        menuBtn.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Circuit schematic: highlight the component under the cursor (hover)
  var circuitLinks = document.querySelectorAll(".circuit-schematic .circuit-link");
  circuitLinks.forEach(function (link) {
    link.addEventListener("mouseenter", function () {
      circuitLinks.forEach(function (l) { l.classList.remove("active"); });
      link.classList.add("active");
    });
    link.addEventListener("mouseleave", function () {
      link.classList.remove("active");
    });
  });
})();
