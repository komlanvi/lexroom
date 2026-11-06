"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api, type Lawyer } from "@/lib/api";

const STORAGE_KEY = "lexroom.lawyerId";

interface IdentityValue {
  lawyers: Lawyer[];
  lawyer: Lawyer;
  lawyerNames: Record<string, string>;
  setLawyerId: (id: string) => void;
}

const IdentityContext = createContext<IdentityValue | null>(null);

export function useIdentity(): IdentityValue {
  const value = useContext(IdentityContext);
  if (value === null) throw new Error("useIdentity must be used inside <IdentityProvider>.");
  return value;
}

/**
 * Who is using the app (TD-7). There is no login: the choice is kept in this browser.
 * Nothing below renders until a known lawyer is chosen.
 */
export function IdentityProvider({ children }: { children: ReactNode }) {
  const [lawyers, setLawyers] = useState<Lawyer[]>();
  const [lawyerId, setLawyerIdState] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLawyerIdState(localStorage.getItem(STORAGE_KEY));
    api.lawyers().then(setLawyers, () => setError(true));
  }, []);

  function setLawyerId(id: string) {
    localStorage.setItem(STORAGE_KEY, id);
    setLawyerIdState(id);
  }

  if (error) return <p className="page-message">The review service cannot be reached. Reload the page to try again.</p>;
  if (lawyers === undefined) return null;

  const lawyer = lawyers.find((candidate) => candidate.id === lawyerId);
  if (lawyer === undefined) return <IdentityPicker lawyers={lawyers} onChoose={setLawyerId} />;

  const lawyerNames = Object.fromEntries(lawyers.map((item) => [item.id, item.name]));
  return (
    <IdentityContext.Provider value={{ lawyers, lawyer, lawyerNames, setLawyerId }}>{children}</IdentityContext.Provider>
  );
}

function IdentityPicker({ lawyers, onChoose }: { lawyers: Lawyer[]; onChoose: (id: string) => void }) {
  const [selected, setSelected] = useState<string>();

  return (
    <div className="dialog-backdrop">
      <form
        className="dialog"
        onSubmit={(event) => {
          event.preventDefault();
          if (selected) onChoose(selected);
        }}
      >
        <h1>Who is using Lexroom?</h1>
        <p className="muted">
          No login in this demo. Your choice is remembered in this browser and can be changed at any time.
        </p>
        <fieldset className="lawyer-options">
          <legend className="visually-hidden">Lawyer</legend>
          {lawyers.map((lawyer) => (
            <label key={lawyer.id}>
              <input
                type="radio"
                name="lawyer"
                value={lawyer.id}
                checked={selected === lawyer.id}
                onChange={() => setSelected(lawyer.id)}
              />
              <span>{lawyer.name}</span>
              <span className="muted">{lawyer.title}</span>
            </label>
          ))}
        </fieldset>
        <div className="dialog-actions">
          <button type="submit" className="button primary" disabled={!selected}>
            Continue
          </button>
        </div>
      </form>
    </div>
  );
}
