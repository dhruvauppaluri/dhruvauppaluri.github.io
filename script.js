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

  // Circuit schematic: scroll spy — highlight the component for the section in view
  var sectionIds = ["about", "skills", "projects", "contact"];
  var sections = sectionIds.map(function (id) { return document.getElementById(id); }).filter(Boolean);
  var circuitLinks = document.querySelectorAll(".circuit-schematic .circuit-link");

  if (sections.length && circuitLinks.length) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var id = entry.target.id;
          circuitLinks.forEach(function (link) {
            if (link.getAttribute("href") === "#" + id) {
              link.classList.add("active");
            } else {
              link.classList.remove("active");
            }
          });
        });
      },
      { rootMargin: "-40% 0px -50% 0px", threshold: 0 }
    );
    sections.forEach(function (section) { observer.observe(section); });
  }
})();
