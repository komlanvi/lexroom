import type { Metadata } from "next";

import { Header } from "@/components/Header";
import { IdentityProvider } from "@/components/Identity";
import { PlanProvider } from "@/components/Plan";

import "./globals.css";

export const metadata: Metadata = {
  title: "Lexroom · Contract review",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <IdentityProvider>
          <PlanProvider>
            <Header />
            <main className="main">{children}</main>
          </PlanProvider>
        </IdentityProvider>
      </body>
    </html>
  );
}
