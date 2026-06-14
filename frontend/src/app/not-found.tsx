import Link from "next/link";
import { Button } from "@/components/ui/button";
import { GoBackButton } from "@/components/GoBackButton";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 text-center">
      <h1 className="text-6xl font-bold tracking-tight">404</h1>
      <h2 className="text-2xl font-semibold">Page Not Found</h2>
      <p className="max-w-md text-muted-foreground">
        The page you&apos;re looking for doesn&apos;t exist or may have been moved.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link href="/">
          <Button>Return to Home</Button>
        </Link>
        <Link href="/dashboard">
        </Link>
        <GoBackButton />
      </div>
    </div>
  );
}