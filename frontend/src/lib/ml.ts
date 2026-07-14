export async function callMl(path: string, token: string, body: unknown) {
  const res = await fetch(`${process.env.ML_SERVICE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`ML service ${res.status}: ${detail.slice(0, 200)}`);
  }
  return res.json();
}

export async function callMlGet(path: string, token: string) {
  const res = await fetch(`${process.env.ML_SERVICE_URL}${path}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`ML service ${res.status}: ${detail.slice(0, 200)}`);
  }
  return res.json();
}
