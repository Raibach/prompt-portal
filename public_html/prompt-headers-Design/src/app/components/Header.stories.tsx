import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import Header from './Header';

const meta = {
  title: 'Components/Header',
  component: Header,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof Header>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    activeTab: 'composer',
  },
};

export const ConsoleActive: Story = {
  args: {
    activeTab: 'console',
  },
};

export const EvaluationActive: Story = {
  args: {
    activeTab: 'evaluation',
  },
};

export const Interactive: Story = {
  render: () => {
    const [activeTab, setActiveTab] = useState('composer');
    
    return (
      <div>
        <Header activeTab={activeTab} onTabChange={setActiveTab} />
        <div className="p-8">
          <p className="text-lg">Active tab: <strong>{activeTab}</strong></p>
          <p className="text-sm text-gray-600 mt-2">Click on different tabs to see the active state change</p>
        </div>
      </div>
    );
  },
};
