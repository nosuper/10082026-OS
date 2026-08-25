import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/deals/$dealCode")({
  component: DealLayout,
});

function DealLayout() {
  return <Outlet />;
}
