import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Leaf, Eye, EyeOff } from "lucide-react";

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { refreshUser } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        await refreshUser();
        navigate("/app/dashboard");
      } else {
        await register(email, password, fullName);
        toast({
          title: "Account created",
          description: "You can now sign in with your credentials.",
        });
        setIsLogin(true);
      }
    } catch (err) {
      toast({
        title: isLogin ? "Login failed" : "Signup failed",
        description: err instanceof Error ? err.message : "Something went wrong",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-hero flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8 shadow-elevated">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Leaf className="w-8 h-8 text-accent" />
            <span className="font-serif text-2xl font-bold text-foreground">TerrAI</span>
          </div>
          <p className="text-sm text-muted-foreground">
            {isLogin ? "Welcome back. Sign in to continue." : "Create your account to get started."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Full Name
              </Label>
              <Input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Your full name"
                required={!isLogin}
              />
            </div>
          )}

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Email
            </Label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Password
            </Label>
            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                minLength={6}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                {isLogin ? "Signing in…" : "Creating account…"}
              </span>
            ) : (
              isLogin ? "Sign In" : "Create Account"
            )}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-sm text-muted-foreground hover:text-accent transition-colors"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>

        {isLogin && (
          <div className="mt-6 pt-5 border-t border-border">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2.5 text-center">
              Quick Demo Fill
            </p>
            <div className="grid grid-cols-3 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-xs h-8"
                onClick={() => {
                  setEmail("admin@terrai.org");
                  setPassword("password123");
                }}
              >
                Admin
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-xs h-8"
                onClick={() => {
                  setEmail("demo@terrai.org");
                  setPassword("password123");
                }}
              >
                CFUG Lead
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-xs h-8"
                onClick={() => {
                  setEmail("validator@terrai.org");
                  setPassword("password123");
                }}
              >
                Validator
              </Button>
            </div>
            <p className="text-[11px] text-muted-foreground text-center mt-2">
              Password: <code className="text-foreground font-mono">password123</code>
            </p>
          </div>
        )}
      </Card>
    </div>
  );
};

export default Auth;
