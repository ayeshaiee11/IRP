// Shared UI behaviour: theme, mobile menu, 3D card tilt, count-up numbers, animated bars, auto-submit.
(function () {
  var root = document.documentElement;
  try { var t = localStorage.getItem("tl-theme"); if (t) root.dataset.theme = t; } catch (e) {}
  document.getElementById("theme").onclick = function () {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem("tl-theme", root.dataset.theme); } catch (e) {}
  };
  document.getElementById("burger").onclick = function () { document.getElementById("side").classList.toggle("open"); };

  document.addEventListener("mousemove", function (e) {
    var c = e.target.closest && e.target.closest(".tilt");
    if (!c) return;
    var r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
    c.style.transform = "perspective(700px) rotateX(" + (-y * 9) + "deg) rotateY(" + (x * 11) + "deg) translateZ(6px)";
  });
  document.addEventListener("mouseout", function (e) {
    var c = e.target.closest && e.target.closest(".tilt");
    if (c && !c.contains(e.relatedTarget)) c.style.transform = "";
  });

  document.querySelectorAll(".count").forEach(function (el) {
    var to = +el.dataset.to, dec = +el.dataset.dec, pre = el.dataset.pre || "", t0 = performance.now();
    (function step(t) {
      var p = Math.min((t - t0) / 1000, 1);
      el.textContent = pre + (to * (1 - Math.pow(1 - p, 3))).toFixed(dec);
      if (p < 1) requestAnimationFrame(step);
    })(t0);
  });

  setTimeout(function () {
    document.querySelectorAll(".bar[data-w]").forEach(function (b) { b.style.width = b.dataset.w + "%"; });
  }, 60);

  document.querySelectorAll("[data-autosubmit]").forEach(function (el) {
    el.addEventListener("change", function () { el.form.submit(); });
  });

  var file = document.getElementById("file"), drop = document.getElementById("drop");
  if (file && drop) {
    file.onchange = function () { document.getElementById("fname").textContent = file.files[0] ? file.files[0].name : "No file chosen"; };
    drop.ondragover = function (e) { e.preventDefault(); drop.classList.add("ov"); };
    drop.ondragleave = function () { drop.classList.remove("ov"); };
    drop.ondrop = function (e) { e.preventDefault(); drop.classList.remove("ov"); file.files = e.dataTransfer.files; file.onchange(); };
  }
})();
