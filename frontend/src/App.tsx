import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/lib/auth";
import { ToastProvider } from "@/components/ui/Toast";
import { ConfirmProvider } from "@/components/ui/ConfirmDialog";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoginPage } from "@/pages/Login";
import { DashboardPage } from "@/pages/Dashboard";
import { DevicesPage } from "@/pages/Devices";
import { EventsPage } from "@/pages/Events";
import { BlacklistPage } from "@/pages/Blacklist";
import { AllowlistPage } from "@/pages/Allowlist";
import { ThreatIntelPage } from "@/pages/ThreatIntel";
import { RulesPage } from "@/pages/Rules";
import { AzurePublishPage } from "@/pages/AzurePublish";
import { UsersPage } from "@/pages/Users";
import { AuditLogPage } from "@/pages/AuditLog";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ConfirmProvider>
          <BrowserRouter>
            <AuthProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route element={<AppLayout />}>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/devices" element={<DevicesPage />} />
                  <Route path="/events" element={<EventsPage />} />
                  <Route path="/blacklist" element={<BlacklistPage />} />
                  <Route path="/allowlist" element={<AllowlistPage />} />
                  <Route path="/threat-intel" element={<ThreatIntelPage />} />
                  <Route path="/rules" element={<RulesPage />} />
                  <Route path="/azure-publish" element={<AzurePublishPage />} />
                  <Route path="/users" element={<UsersPage />} />
                  <Route path="/audit-log" element={<AuditLogPage />} />
                </Route>
              </Routes>
            </AuthProvider>
          </BrowserRouter>
        </ConfirmProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
