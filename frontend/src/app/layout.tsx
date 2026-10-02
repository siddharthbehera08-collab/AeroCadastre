import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AeroCadastre — AI-Assisted Urban Cadastral Intelligence | SIH26012",
  description:
    "AI-assisted urban parcel mapping, multi-agent cadastral intelligence, and human-in-the-loop field verification platform (DoLR / MoRD Prototype).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F4F1EA] text-[#171615] antialiased selection:bg-[#B89A78]/30 selection:text-[#171615]">
        {children}
      </body>
    </html>
  );
}
