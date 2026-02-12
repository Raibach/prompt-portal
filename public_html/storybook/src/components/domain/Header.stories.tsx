import type { Meta, StoryObj } from '@storybook/react';
import { Header } from './Header';
import './Header.css';

const meta: Meta<typeof Header> = {
  title: 'Domain/Header',
  component: Header,
  parameters: {
    layout: 'fullscreen',
    design: {
      type: 'figma',
      url: 'https://www.figma.com/file/...', // Add Figma URL here
    },
  },
  tags: ['autodocs'],
  argTypes: {
    title: {
      control: 'text',
      description: 'Site title to display',
    },
    logoUrl: {
      control: 'text',
      description: 'Logo URL or path',
    },
    sticky: {
      control: 'boolean',
      description: 'Whether the header is sticky',
    },
    backgroundColor: {
      control: 'color',
      description: 'Background color',
    },
    textColor: {
      control: 'color',
      description: 'Text color',
    },
    className: {
      control: 'text',
      description: 'Custom CSS class name',
    },
    onLogoClick: {
      action: 'logo clicked',
      description: 'Callback when logo is clicked',
    },
    onTitleClick: {
      action: 'title clicked',
      description: 'Callback when title is clicked',
    },
    onProfileClick: {
      action: 'profile clicked',
      description: 'Callback when user profile is clicked',
    },
    showSearch: {
      control: 'boolean',
      description: 'Whether to show search bar',
    },
    searchPlaceholder: {
      control: 'text',
      description: 'Search placeholder text',
    },
    onSearch: {
      action: 'search performed',
      description: 'Callback when search is performed',
    },
  },
};

export default meta;
type Story = StoryObj<typeof Header>;

/**
 * Default Header
 */
export const Default: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    searchPlaceholder: 'Search prompts, templates...',
  },
};

/**
 * Header with Logo
 */
export const WithLogo: Story = {
  args: {
    title: 'Prompt Portal',
    logoUrl: 'https://via.placeholder.com/40x40/3b82f6/ffffff?text=PP',
    sticky: true,
    showSearch: true,
  },
};

/**
 * Header with User Profile
 */
export const WithUserProfile: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    userProfile: {
      name: 'John Doe',
      email: 'john@example.com',
      avatarUrl: 'https://via.placeholder.com/32x32/3b82f6/ffffff?text=JD',
    },
  },
};

/**
 * Header with Custom Navigation
 */
export const WithCustomNavigation: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    navItems: [
      { label: 'Home', href: '/', active: true },
      { label: 'Prompts', href: '/prompts' },
      { label: 'Templates', href: '/templates' },
      { label: 'Analytics', href: '/analytics' },
      { label: 'Settings', href: '/settings' },
      { label: 'Help', href: '/help' },
    ],
  },
};

/**
 * Header without Search
 */
export const WithoutSearch: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: false,
    userProfile: {
      name: 'Jane Smith',
      avatarUrl: 'https://via.placeholder.com/32x32/10b981/ffffff?text=JS',
    },
  },
};

/**
 * Header with Custom Colors
 */
export const WithCustomColors: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    backgroundColor: '#1e293b',
    textColor: '#f8fafc',
    userProfile: {
      name: 'Alex Johnson',
      avatarUrl: 'https://via.placeholder.com/32x32/8b5cf6/ffffff?text=AJ',
    },
  },
};

/**
 * Non-Sticky Header
 */
export const NonSticky: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: false,
    showSearch: true,
  },
};

/**
 * Header with Long Title
 */
export const WithLongTitle: Story = {
  args: {
    title: 'Prompt Portal Design System',
    sticky: true,
    showSearch: true,
    userProfile: {
      name: 'Sarah Williams',
      avatarUrl: 'https://via.placeholder.com/32x32/ef4444/ffffff?text=SW',
    },
  },
};

/**
 * Header with Many Navigation Items
 */
export const WithManyNavigationItems: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    navItems: [
      { label: 'Dashboard', href: '/', active: true },
      { label: 'Prompts', href: '/prompts' },
      { label: 'Templates', href: '/templates' },
      { label: 'Analytics', href: '/analytics' },
      { label: 'Settings', href: '/settings' },
      { label: 'Team', href: '/team' },
      { label: 'Billing', href: '/billing' },
      { label: 'Support', href: '/support' },
    ],
  },
};

/**
 * Header with Search Focused
 */
export const WithSearchFocused: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    searchPlaceholder: 'Type to search...',
  },
  parameters: {
    pseudo: {
      focus: '.header__search-input',
    },
  },
};

/**
 * Header with Search Query
 */
export const WithSearchQuery: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    searchPlaceholder: 'Search...',
  },
  parameters: {
    pseudo: {
      text: '.header__search-input',
      content: 'prompt templates',
    },
  },
};

/**
 * Interactive Header
 */
export const Interactive: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    userProfile: {
      name: 'Interactive User',
      avatarUrl: 'https://via.placeholder.com/32x32/f59e0b/ffffff?text=IU',
    },
  },
};

/**
 * Minimal Header
 */
export const Minimal: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: false,
    navItems: [
      { label: 'Home', href: '/' },
      { label: 'About', href: '/about' },
    ],
  },
};

/**
 * Header with Custom Logo Placeholder
 */
export const WithCustomLogoPlaceholder: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    // No logoUrl provided, will use placeholder
  },
};

/**
 * Header with Avatar Placeholder
 */
export const WithAvatarPlaceholder: Story = {
  args: {
    title: 'Prompt Portal',
    sticky: true,
    showSearch: true,
    userProfile: {
      name: 'Michael Brown',
      // No avatarUrl provided, will use placeholder with initials
    },
  },
};

/**
 * Header with All Features
 */
export const WithAllFeatures: Story = {
  args: {
    title: 'Prompt Portal Pro',
    logoUrl: 'https://via.placeholder.com/40x40/6366f1/ffffff?text=PP',
    sticky: true,
    backgroundColor: '#0f172a',
    textColor: '#f1f5f9',
    showSearch: true,
    searchPlaceholder: 'Search across all prompts and templates...',
    navItems: [
      { label: 'Dashboard', href: '/', active: true },
      { label: 'Prompts', href: '/prompts' },
      { label: 'Templates', href: '/templates' },
      { label: 'Analytics', href: '/analytics' },
      { label: 'Team', href: '/team' },
      { label: 'Settings', href: '/settings' },
    ],
    userProfile: {
      name: 'Admin User',
      email: 'admin@promptportal.com',
      avatarUrl: 'https://via.placeholder.com/32x32/8b5cf6/ffffff?text=AU',
    },
  },
};