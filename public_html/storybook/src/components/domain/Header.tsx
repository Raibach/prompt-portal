import React from 'react';
import './Header.css';

export interface HeaderProps {
  /** Site title to display */
  title?: string;
  /** Logo URL or path */
  logoUrl?: string;
  /** Whether the header is sticky */
  sticky?: boolean;
  /** Background color */
  backgroundColor?: string;
  /** Text color */
  textColor?: string;
  /** Custom CSS class name */
  className?: string;
  /** Callback when logo is clicked */
  onLogoClick?: () => void;
  /** Callback when title is clicked */
  onTitleClick?: () => void;
  /** Navigation items */
  navItems?: Array<{
    label: string;
    href?: string;
    onClick?: () => void;
    active?: boolean;
  }>;
  /** User profile information */
  userProfile?: {
    name?: string;
    avatarUrl?: string;
    email?: string;
  };
  /** Callback when user profile is clicked */
  onProfileClick?: () => void;
  /** Whether to show search bar */
  showSearch?: boolean;
  /** Search placeholder text */
  searchPlaceholder?: string;
  /** Callback when search is performed */
  onSearch?: (query: string) => void;
}

/**
 * Header Component
 * 
 * A flexible site header component with logo, navigation, search, and user profile.
 * Designed for use across the Prompt Portal application.
 */
export const Header: React.FC<HeaderProps> = ({
  title = 'Prompt Portal',
  logoUrl,
  sticky = true,
  backgroundColor = 'var(--color-background)',
  textColor = 'var(--color-text)',
  className = '',
  onLogoClick,
  onTitleClick,
  navItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Prompts', href: '/prompts' },
    { label: 'Templates', href: '/templates' },
    { label: 'Analytics', href: '/analytics' },
    { label: 'Settings', href: '/settings' },
  ],
  userProfile,
  onProfileClick,
  showSearch = true,
  searchPlaceholder = 'Search prompts, templates...',
  onSearch,
}) => {
  const [searchQuery, setSearchQuery] = React.useState('');
  const [isSearchFocused, setIsSearchFocused] = React.useState(false);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && onSearch && searchQuery.trim()) {
      onSearch(searchQuery.trim());
    }
  };

  return (
    <header
      className={`header ${sticky ? 'header--sticky' : ''} ${className}`}
      style={{
        backgroundColor,
        color: textColor,
      }}
      role="banner"
      aria-label="Site header"
    >
      <div className="header__container">
        {/* Logo and Title Section */}
        <div className="header__brand">
          {logoUrl ? (
            <button
              className="header__logo-button"
              onClick={onLogoClick}
              type="button"
              aria-label="Go to homepage"
            >
              <img
                src={logoUrl}
                alt={`${title} logo`}
                className="header__logo"
              />
            </button>
          ) : (
            <div className="header__logo-placeholder">
              <svg
                className="header__logo-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
          )}
          
          <button
            className="header__title-button"
            onClick={onTitleClick}
            type="button"
            aria-label="Go to homepage"
          >
            <h1 className="header__title">{title}</h1>
          </button>
        </div>

        {/* Navigation Section */}
        <nav className="header__nav" aria-label="Main navigation">
          <ul className="header__nav-list">
            {navItems.map((item, index) => (
              <li key={index} className="header__nav-item">
                {item.href ? (
                  <a
                    href={item.href}
                    className={`header__nav-link ${item.active ? 'header__nav-link--active' : ''}`}
                    onClick={(e) => {
                      if (item.onClick) {
                        e.preventDefault();
                        item.onClick();
                      }
                    }}
                    aria-current={item.active ? 'page' : undefined}
                  >
                    {item.label}
                  </a>
                ) : (
                  <button
                    className={`header__nav-button ${item.active ? 'header__nav-button--active' : ''}`}
                    onClick={item.onClick}
                    type="button"
                    aria-current={item.active ? 'page' : undefined}
                  >
                    {item.label}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </nav>

        {/* Search and Profile Section */}
        <div className="header__actions">
          {showSearch && (
            <form
              className="header__search-form"
              onSubmit={handleSearchSubmit}
              role="search"
              aria-label="Site search"
            >
              <div className={`header__search-container ${isSearchFocused ? 'header__search-container--focused' : ''}`}>
                <svg
                  className="header__search-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="11" cy="11" r="8" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
                <input
                  type="search"
                  className="header__search-input"
                  placeholder={searchPlaceholder}
                  value={searchQuery}
                  onChange={handleSearchChange}
                  onKeyDown={handleKeyDown}
                  onFocus={() => setIsSearchFocused(true)}
                  onBlur={() => setIsSearchFocused(false)}
                  aria-label="Search"
                />
                {searchQuery && (
                  <button
                    type="button"
                    className="header__search-clear"
                    onClick={() => setSearchQuery('')}
                    aria-label="Clear search"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </form>
          )}

          {userProfile && (
            <button
              className="header__profile-button"
              onClick={onProfileClick}
              type="button"
              aria-label="User profile menu"
            >
              {userProfile.avatarUrl ? (
                <img
                  src={userProfile.avatarUrl}
                  alt={userProfile.name || 'User avatar'}
                  className="header__profile-avatar"
                />
              ) : (
                <div className="header__profile-avatar-placeholder">
                  {userProfile.name?.[0]?.toUpperCase() || 'U'}
                </div>
              )}
              {userProfile.name && (
                <span className="header__profile-name">{userProfile.name}</span>
              )}
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;