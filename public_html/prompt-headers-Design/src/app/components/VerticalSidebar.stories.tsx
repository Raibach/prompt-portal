import type { Meta, StoryObj } from '@storybook/react';
import VerticalSidebar from './VerticalSidebar';

const meta = {
  title: 'Components/VerticalSidebar',
  component: VerticalSidebar,
  parameters: {
    layout: 'fullscreen',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof VerticalSidebar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <div style={{ height: '100vh', position: 'relative' }}>
      <VerticalSidebar />
    </div>
  ),
};
