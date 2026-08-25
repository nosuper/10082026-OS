import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/my-work")({
  component: () => <Outlet />,
});
