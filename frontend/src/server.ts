const isProduction = process.env.NODE_ENV === "production";

async function clientAsset() {
  if (isProduction) return new Response(Bun.file("./dist/assets/main.js"));
  const result = await Bun.build({ entrypoints: ["./src/main.tsx"], target: "browser", minify: false });
  if (!result.success) return new Response(result.logs.map((log) => log.message).join("\n"), { status: 500 });
  return new Response(result.outputs[0], { headers: { "Content-Type": "application/javascript" } });
}

Bun.serve({
  port: Number(process.env.PORT || 3000),
  routes: {
    "/": isProduction ? new Response(Bun.file("./dist/index.html")) : new Response(Bun.file("./index.html")),
    "/assets/main.js": clientAsset,
    "/src/main.tsx": clientAsset,
    "/assets/main.css": new Response(Bun.file(isProduction ? "./dist/assets/main.css" : "./src/style.css"), { headers: { "Content-Type": "text/css" } }),
    "/src/style.css": new Response(Bun.file("./src/style.css"), { headers: { "Content-Type": "text/css" } }),
  },
  fetch() {
    return new Response("Not found", { status: 404 });
  },
});

console.log(`Document cropper running at http://localhost:${process.env.PORT || 3000}`);
