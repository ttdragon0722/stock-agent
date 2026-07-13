import type { Metadata } from "next";

import EventsPageClient from "@/components/EventsPageClient";

export const metadata: Metadata = {
  title: "重要事件與關鍵日期 | Invest Advisor",
  description: "決策報告萃取的重要事件與關鍵日期時間軸",
};

export default function EventsPage() {
  return <EventsPageClient />;
}
