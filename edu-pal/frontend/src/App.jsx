// Main app component that handles role selection and renders the appropriate dashboard
import { useState } from 'react';
import RoleSelector from './components/RoleSelector';
import TeacherDashboard from './components/TeacherDashboard';
import StudentDashboard from './components/StudentDashboard';

function App() {
  const [userRole, setUserRole] = useState(null);
  // Shows role selector first as a dropdown, then teacher/student dashboard
}