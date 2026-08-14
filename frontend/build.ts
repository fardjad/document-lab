const client = await Bun.build({
  entrypoints: ["./src/main.tsx"],
  outdir: "./dist/assets",
  target: "browser",
  minify: true,
  naming: "[name].[ext]",
});

if (!client.success) {
  console.error(...client.logs);
  process.exit(1);
}

const server = await Bun.build({
  entrypoints: ["./src/server.ts"],
  outdir: "./dist",
  target: "bun",
  minify: true,
  naming: "server.js",
});

if (!server.success) {
  console.error(...server.logs);
  process.exit(1);
}

await Bun.write("./dist/index.html", `<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Document Cropper</title><link rel="stylesheet" href="/assets/main.css"></head>
<body><div id="app"></div><script src="/assets/main.js"></script></body></html>`);
console.log("Built dist/server.js and dist/assets/main.js");
