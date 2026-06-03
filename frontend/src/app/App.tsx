import { RouterProvider } from "react-router-dom";
import { ThemeProvider } from "./providers/ThemeProvider";
import { ModeProvider } from "./providers/ModeProvider";
import { router } from "./router";

export function App() {
  return (
    <ThemeProvider>
      <ModeProvider>
        <RouterProvider router={router} />
      </ModeProvider>
    </ThemeProvider>
  );
}
