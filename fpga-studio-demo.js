(function () {
  var root = document.getElementById("fpga-demo");
  if (!root) return;

  var logEl = document.getElementById("fpga-demo-log");
  var statusEl = document.getElementById("fpga-demo-status");
  var buttons = {
    validate: root.querySelector('[data-action="validate"]'),
    simulate: root.querySelector('[data-action="simulate"]'),
    build: root.querySelector('[data-action="build"]'),
    program: root.querySelector('[data-action="program"]')
  };
  var busy = false;

  var scripts = {
    validate: [
      "Checking C5G Blinky…",
      "rtl/blinky.sv  top = blinky",
      "constraints/c5g.qsf  CLOCK_50_B5B → PIN_R20",
      "constraints/c5g.qsf  LEDG[0] → PIN_L7  2.5 V",
      "No duplicate pins, no missing ports.",
      "Validate succeeded."
    ],
    simulate: [
      "Running blinky_tb with Icarus Verilog…",
      "CLOCK_50_B5B  LEDG0  sampled in waves.vcd",
      "0 errors  0 warnings",
      "Simulate succeeded."
    ],
    build: [
      "Yosys  synth_intel_alm -top blinky",
      "nextpnr-mistral  --device 5CGXFC5C6F27C7",
      "Max frequency for clock 'CLOCK_50_B5B': 183.59 MHz (PASS at 50.00 MHz)",
      "Wrote .fpga/build/release/design.rbf",
      "Build succeeded."
    ],
    program: [
      "openFPGALoader  -b c5g --write-sram design.rbf",
      "JTAG  USB-Blaster  5CGXFC5C6F27C7",
      "Load SRAM  100%",
      "LEDG0 is toggling from counter[22]. Power-cycle clears SRAM."
    ]
  };

  function setLog(text) {
    logEl.textContent = text;
    logEl.scrollTop = logEl.scrollHeight;
  }

  function typeLines(lines, done) {
    var i = 0;
    var acc = "";
    function step() {
      if (i >= lines.length) {
        done();
        return;
      }
      acc += (acc ? "\n" : "") + lines[i];
      setLog(acc);
      i += 1;
      window.setTimeout(step, 220);
    }
    step();
  }

  function run(action) {
    if (busy || buttons[action].disabled) return;
    busy = true;
    Object.keys(buttons).forEach(function (key) {
      buttons[key].disabled = true;
    });
    statusEl.textContent = action === "program" ? "Programming SRAM…" : "Running…";
    statusEl.style.color = "#ffd60a";
    root.setAttribute("data-programmed", "0");

    typeLines(scripts[action], function () {
      busy = false;
      if (action === "validate") {
        buttons.validate.disabled = false;
        buttons.simulate.disabled = false;
        buttons.build.disabled = false;
        buttons.program.disabled = true;
        statusEl.textContent = "C5G Connected";
        statusEl.style.color = "#30d158";
      } else if (action === "simulate") {
        buttons.validate.disabled = false;
        buttons.simulate.disabled = false;
        buttons.build.disabled = false;
        buttons.program.disabled = true;
        statusEl.textContent = "C5G Connected";
        statusEl.style.color = "#30d158";
      } else if (action === "build") {
        buttons.validate.disabled = false;
        buttons.simulate.disabled = false;
        buttons.build.disabled = false;
        buttons.program.disabled = false;
        statusEl.textContent = "Bitstream ready";
        statusEl.style.color = "#30d158";
      } else {
        buttons.validate.disabled = false;
        buttons.simulate.disabled = false;
        buttons.build.disabled = false;
        buttons.program.disabled = false;
        statusEl.textContent = "SRAM programmed";
        statusEl.style.color = "#30d158";
        root.setAttribute("data-programmed", "1");
      }
    });
  }

  Object.keys(buttons).forEach(function (action) {
    buttons[action].addEventListener("click", function () {
      run(action);
    });
  });
})();
