export function save(data) {
  try {
    localStorage.setItem("x", JSON.stringify(data));
  } catch (e) {}
}
