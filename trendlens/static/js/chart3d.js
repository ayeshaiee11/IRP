// 3D chart (Three.js): bars = actual values, translucent bars = forecast, white tube = trendline, red ribbon = 95% range.
(function () {
  var box = document.getElementById("gl"), data = JSON.parse(document.getElementById("tl-data").textContent);
  if (!box) return;
  var renderer;
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
  catch (e) { box.innerHTML = '<p class="small">The 3D chart needs WebGL, which is not available in this browser.</p>'; return; }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  var W = box.clientWidth, H = 360;
  renderer.setSize(W, H);
  box.appendChild(renderer.domElement);

  var scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(42, W / H, .1, 200);
  scene.add(new THREE.AmbientLight(0xffffff, .55));
  var sun = new THREE.DirectionalLight(0xffffff, .9); sun.position.set(6, 12, 8); scene.add(sun);
  var glow = new THREE.PointLight(0xd63a52, 1.1, 60); glow.position.set(-8, 6, 6); scene.add(glow);

  var n = data.values.length, h = data.forecast.length, N = n + h;
  var top = Math.max.apply(null, data.values.concat(data.forecast.map(function (f) { return f.upper; })));
  var sc = 6 / top, X = function (i) { return i - (N - 1) / 2; };
  var group = new THREE.Group(), bars = [];

  for (var i = 0; i < N; i++) {
    var v = i < n ? data.values[i] : data.forecast[i - n].value, g = Math.max(v * sc, .05);
    var geo = new THREE.BoxGeometry(.64, g, .9); geo.translate(0, g / 2, 0);
    var mat = i < n
      ? new THREE.MeshStandardMaterial({ color: 0x9b2236, metalness: .35, roughness: .35 })
      : new THREE.MeshStandardMaterial({ color: 0xCBC0B2, transparent: true, opacity: .6, metalness: .2, roughness: .5 });
    var m = new THREE.Mesh(geo, mat); m.position.x = X(i); m.scale.y = .001; group.add(m); bars.push(m);
  }
  var p0 = new THREE.Vector3(X(0), data.intercept * sc, .6), p1 = new THREE.Vector3(X(N - 1), (data.intercept + data.slope * (N - 1)) * sc, .6);
  group.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.LineCurve3(p0, p1), 2, .055, 8), new THREE.MeshBasicMaterial({ color: 0xF8F8F7 })));

  var shape = new THREE.Shape();
  shape.moveTo(X(n - 1), data.fitted[n - 1] * sc);
  data.forecast.forEach(function (f, k) { shape.lineTo(X(n + k), f.upper * sc); });
  for (var k = h - 1; k >= 0; k--) shape.lineTo(X(n + k), data.forecast[k].lower * sc);
  var band = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial({ color: 0xd63a52, transparent: true, opacity: .3, side: THREE.DoubleSide }));
  band.position.z = .6; group.add(band);

  var grid = new THREE.GridHelper(N + 4, N + 4, 0x7E6961, 0x3a2528); grid.position.y = -.01; group.add(grid);
  group.rotation.set(.18, -.5, 0); scene.add(group);
  camera.position.set(0, N * .3 + 2.5, N * .75 + 4); camera.lookAt(0, 2.4, 0);

  var drag = false, lx = 0, ly = 0, t0 = performance.now(), c = renderer.domElement;
  c.onpointerdown = function (e) { drag = true; lx = e.clientX; ly = e.clientY; c.setPointerCapture(e.pointerId); };
  c.onpointermove = function (e) {
    if (!drag) return;
    group.rotation.y += (e.clientX - lx) * .01;
    group.rotation.x = Math.max(-.15, Math.min(.6, group.rotation.x + (e.clientY - ly) * .005));
    lx = e.clientX; ly = e.clientY;
  };
  c.onpointerup = function () { drag = false; };
  addEventListener("resize", function () { var w = box.clientWidth; renderer.setSize(w, H); camera.aspect = w / H; camera.updateProjectionMatrix(); });

  (function loop() {
    requestAnimationFrame(loop);
    var t = (performance.now() - t0) / 1000;
    bars.forEach(function (b, i) { var p = Math.min(Math.max((t - i * .07) / .8, 0), 1); b.scale.y = Math.max(1 - Math.pow(1 - p, 3), .001); });
    if (!drag) group.rotation.y += .002;
    renderer.render(scene, camera);
  })();
})();
