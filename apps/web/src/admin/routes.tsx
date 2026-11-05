import { Route, Routes } from 'react-router-dom';
import { ApplicationDetail, Applications } from './Applications';
import { Dashboard } from './Dashboard';
import { AdminBookings, AuditLog } from './Lists';
import { Safety } from './Safety';
import { AdminLayout } from './shared';
import { Deletions, SupportQueue } from './Support';
import { Users } from './Users';

export default function AdminRoutes() {
  return (
    <Routes>
      <Route element={<AdminLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="applications" element={<Applications />} />
        <Route path="applications/:id" element={<ApplicationDetail />} />
        <Route path="safety" element={<Safety />} />
        <Route path="users" element={<Users />} />
        <Route path="support" element={<SupportQueue />} />
        <Route path="deletions" element={<Deletions />} />
        <Route path="bookings" element={<AdminBookings />} />
        <Route path="audit" element={<AuditLog />} />
      </Route>
    </Routes>
  );
}
