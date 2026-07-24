export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <nav>Dashboard Sidebar Placeholder</nav>
      <main>{children}</main>
    </div>
  );
}
