import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { AboutIndexPage, AboutPage } from "./AboutPage.jsx";
import { App } from "./App.jsx";
import { WorkflowPage } from "./WorkflowPage.jsx";
import "./styles.css";

const root = document.getElementById("root");
createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/workflow" element={<WorkflowPage />} />
        <Route path="/about" element={<AboutIndexPage />} />
        <Route path="/about/:slug" element={<AboutPage />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
