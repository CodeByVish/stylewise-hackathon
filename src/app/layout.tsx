import type { Metadata } from "next";
import { Suspense } from "react";
import ScrollReveal from "@/components/scroll-reveal";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stylewise Fit Lab",
  description: "See how every size sits on your shape, from real brand size charts and a measured body model.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}<Suspense fallback={null}><ScrollReveal /></Suspense></body>
    </html>
  );
}
