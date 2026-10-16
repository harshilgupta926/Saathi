import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Household demo | Saathi",
  description: "Explore Saathi's household demo. Live SMS, provider integrations, automatic reminders and volunteer assignment require separate configuration and verification.",
  robots: { index: false, follow: false },
};

export default function DashboardLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}