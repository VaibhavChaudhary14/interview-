"use client";

export function BrowseNavLink() {
  return (
    <a
      href="/browse"
      id="nav-browse-roles"
      style={{
        fontSize: "0.8125rem",
        fontWeight: 500,
        color: "#a5b4fc",
        textDecoration: "none",
        padding: "6px 14px",
        borderRadius: "8px",
        border: "1px solid rgba(99,102,241,0.3)",
        transition: "background 0.15s, border-color 0.15s",
        whiteSpace: "nowrap",
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLAnchorElement).style.background = "rgba(99,102,241,0.12)";
        (e.currentTarget as HTMLAnchorElement).style.borderColor = "rgba(99,102,241,0.5)";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLAnchorElement).style.background = "transparent";
        (e.currentTarget as HTMLAnchorElement).style.borderColor = "rgba(99,102,241,0.3)";
      }}
    >
      🎯 Browse Roles
    </a>
  );
}
