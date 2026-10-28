import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stylewise Fit Lab",
  description: "Explore wardrobe-aware outfits and evidence-based fit decisions.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
