import type { NextRequest } from "next/server";

// Read at request time, so the same build works locally and in Docker.
const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function forward(request: NextRequest, { params }: RouteContext<"/api/[...path]">) {
  const { path } = await params;
  const headers = new Headers();
  const lawyerId = request.headers.get("x-lawyer-id");
  if (lawyerId) headers.set("X-Lawyer-Id", lawyerId);

  try {
    const response = await fetch(`${API_URL}/api/${path.join("/")}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      cache: "no-store",
    });
    return new Response(response.body, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
    });
  } catch {
    return Response.json(
      { code: "API_UNAVAILABLE", message: "The review service cannot be reached.", details: {} },
      { status: 502 },
    );
  }
}

export { forward as GET, forward as POST };
