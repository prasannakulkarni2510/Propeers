// Turn an image the operator attaches in chat into a data: URL small enough
// to send. Screenshots are mostly text, so small PNGs are kept as they are
// (crisp); anything big is scaled to MAX_SIDE and re-encoded as JPEG.

export const MAX_IMAGES = 3;
const MAX_SIDE = 1600;
const KEEP_PNG_BYTES = 1.5 * 1024 * 1024;
const MAX_INPUT_BYTES = 20 * 1024 * 1024;
const TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

const readAsDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = () => reject(new Error("Couldn't read that file."));
    r.readAsDataURL(file);
  });

const loadImage = (src) =>
  new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("That file isn't an image the browser can open."));
    img.src = src;
  });

export async function prepareImage(file) {
  if (!TYPES.includes(file.type)) throw new Error("Attach a PNG, JPEG, WebP or GIF image.");
  if (file.size > MAX_INPUT_BYTES) throw new Error("That image is over 20 MB.");
  const original = await readAsDataUrl(file);
  const img = await loadImage(original);
  const longest = Math.max(img.naturalWidth, img.naturalHeight);
  if (longest <= MAX_SIDE && file.type === "image/png" && file.size <= KEEP_PNG_BYTES) {
    return original;
  }
  const scale = Math.min(1, MAX_SIDE / longest);
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(img.naturalWidth * scale);
  canvas.height = Math.round(img.naturalHeight * scale);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff"; // transparent PNG areas would turn black in JPEG
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.9);
}

export const imageFiles = (list) => [...(list || [])].filter((f) => f.type.startsWith("image/"));
