import { RouterProvider } from "react-router-dom";
import { ThemeProvider } from "./providers/ThemeProvider";
import { ModeProvider } from "./providers/ModeProvider";
import { QueryProvider } from "./providers/QueryProvider";
import { router } from "./router";

export function App() {
  return (
    <QueryProvider>
      <ThemeProvider>
        <ModeProvider>
          <RouterProvider router={router} />
        </ModeProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
