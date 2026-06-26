(function () {
  var yearSpan = document.getElementById("year");
  if (yearSpan) {
    yearSpan.textContent = new Date().getFullYear();
  }

  var menuBtn = document.querySelector(".menu-btn");
  var nav = document.querySelector(".nav");

  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
  }

  // --- Circuit spine: full-page trace that energizes as the user scrolls ---
  var spine = document.querySelector(".circuit-spine");
  if (spine) {
    var svg = spine.querySelector(".circuit-spine__svg");
    var baseWire = spine.querySelector(".circuit-spine__wire--base");
    var liveWire = spine.querySelector(".circuit-spine__wire--live");
    var nodeGroup = spine.querySelector(".circuit-spine__nodes");
    var waypointSelectors = [".hero", "#about", "#skills", "#projects", "#contact", ".footer"];
    var trunkX = 28;
    var jogReach = 18;
    var jogHalf = 16;
    var nodes = [];
    var liveLength = 0;
    var docHeight = 0;
    var rafPending = false;

    function ns(tag) {
      return document.createElementNS("http://www.w3.org/2000/svg", tag);
    }

    function build() {
      var waypoints = waypointSelectors
        .map(function (sel) {
          var el = document.querySelector(sel);
          if (!el) return null;
          var rect = el.getBoundingClientRect();
          return { y: rect.top + window.scrollY + 2 };
        })
        .filter(Boolean)
        .sort(function (a, b) {
          return a.y - b.y;
        });

      docHeight = document.documentElement.scrollHeight;
      var docWidth = svg.clientWidth || window.innerWidth;
      svg.setAttribute("viewBox", "0 0 " + docWidth + " " + docHeight);
      svg.setAttribute("preserveAspectRatio", "none");

      var d = "M " + trunkX + " 0";
      waypoints.forEach(function (wp) {
        d += " L " + trunkX + " " + (wp.y - jogHalf);
        d += " L " + (trunkX + jogReach) + " " + (wp.y - jogHalf);
        d += " L " + (trunkX + jogReach) + " " + (wp.y + jogHalf);
        d += " L " + trunkX + " " + (wp.y + jogHalf);
      });
      d += " L " + trunkX + " " + docHeight;

      baseWire.setAttribute("d", d);
      liveWire.setAttribute("d", d);
      liveLength = liveWire.getTotalLength();
      liveWire.style.strokeDasharray = liveLength;

      nodeGroup.innerHTML = "";
      nodes = waypoints.map(function (wp) {
        var circle = ns("circle");
        circle.setAttribute("cx", trunkX + jogReach);
        circle.setAttribute("cy", wp.y);
        circle.setAttribute("r", 4.5);
        circle.setAttribute("class", "circuit-spine__node");
        nodeGroup.appendChild(circle);
        return { y: wp.y, el: circle };
      });

      update();
    }

    function update() {
      var viewportMid = window.scrollY + window.innerHeight * 0.45;
      var progress = docHeight > 0 ? Math.min(1, Math.max(0, viewportMid / docHeight)) : 0;
      liveWire.style.strokeDashoffset = liveLength * (1 - progress);

      nodes.forEach(function (node) {
        if (viewportMid >= node.y) {
          node.el.classList.add("is-active");
        } else {
          node.el.classList.remove("is-active");
        }
      });

      rafPending = false;
    }

    function onScroll() {
      if (!rafPending) {
        rafPending = true;
        requestAnimationFrame(update);
      }
    }

    var resizeTimer;
    function onResize() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(build, 150);
    }

    window.addEventListener("load", build);
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onScroll, { passive: true });
    if (document.readyState === "complete") {
      build();
    }
  }
})();

