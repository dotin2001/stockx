import { AuthForm } from "@/components/auth/auth-form";

export default function SignupPage() {
  return (
    <div className="page-shell py-10">
      <AuthForm mode="signup" />
    </div>
  );
}
