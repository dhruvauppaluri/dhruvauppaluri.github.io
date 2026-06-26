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
    var edgeMargin = 28;
    var nodes = [];
    var liveLength = 0;
    var docHeight = 0;
    var rafPending = false;

    function ns(tag) {
      return document.createElementNS("http://www.w3.org/2000/svg", tag);
    }

    function build() {
      docHeight = document.documentElement.scrollHeight;
      var docWidth = svg.clientWidth || window.innerWidth;
      svg.setAttribute("viewBox", "0 0 " + docWidth + " " + docHeight);
      svg.setAttribute("preserveAspectRatio", "none");

      var sections = waypointSelectors
        .map(function (sel, idx) {
          var el = document.querySelector(sel);
          if (!el) return null;
          var rect = el.getBoundingClientRect();
          var side = idx % 2 === 0 ? "left" : "right";
          var x = side === "left" ? rect.left - edgeMargin : rect.right + edgeMargin;
          x = Math.max(14, Math.min(docWidth - 14, x));
          return {
            x: x,
            top: rect.top + window.scrollY,
            bottom: rect.top + rect.height + window.scrollY
          };
        })
        .filter(Boolean)
        .sort(function (a, b) {
          return a.top - b.top;
        });

      // Each section gets an entry/exit pair at the same x, so the trace runs straight
      // down beside the text for the section's full height — it only swings across the
      // page (through the center) in the empty gap between one section and the next.
      var nodeWaypoints = [];
      var points = [{ x: sections[0].x, y: 0 }];
      sections.forEach(function (s) {
        var entry = { x: s.x, y: s.top + 16 };
        var exit = { x: s.x, y: s.bottom - 16 };
        points.push(entry, exit);
        nodeWaypoints.push(entry);
      });
      points.push({ x: sections[sections.length - 1].x, y: docHeight });

      var d = "M " + points[0].x + " " + points[0].y;
      for (var i = 1; i < points.length; i++) {
        var p0 = points[i - 1];
        var p1 = points[i];
        if (p0.x === p1.x) {
          d += " L " + p1.x + " " + p1.y;
        } else {
          var midY = (p0.y + p1.y) / 2;
          d += " C " + p0.x + " " + midY + ", " + p1.x + " " + midY + ", " + p1.x + " " + p1.y;
        }
      }
      var waypoints = nodeWaypoints;

      baseWire.setAttribute("d", d);
      liveWire.setAttribute("d", d);
      liveLength = liveWire.getTotalLength();
      liveWire.style.strokeDasharray = liveLength;

      nodeGroup.innerHTML = "";
      nodes = waypoints.map(function (wp) {
        var circle = ns("circle");
        circle.setAttribute("cx", wp.x);
        circle.setAttribute("cy", wp.y);
        circle.setAttribute("r", 5);
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

