import type { Metadata } from "next";

import { Header } from "@/components/Header";
import { IdentityProvider } from "@/components/Identity";

import "./globals.css";

export const metadata: Metadata = {
  title: "Lexroom · Contract review",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <IdentityProvider>
          <Header />
          <main className="main">{children}</main>
        </IdentityProvider>
      </body>
    </html>
  );
}
