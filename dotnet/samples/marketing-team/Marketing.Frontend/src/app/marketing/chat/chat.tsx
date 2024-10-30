"use client";

import * as React from 'react';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Public from '@mui/icons-material/Public';
import KeyboardArrowDown from '@mui/icons-material/KeyboardArrowDown';
import HandshakeTwoToneIcon from '@mui/icons-material/HandshakeTwoTone';
import WorkspacePremiumTwoToneIcon from '@mui/icons-material/WorkspacePremiumTwoTone';
import { styled } from '@mui/material/styles';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import { Button, Container, Grid, TextField } from '@mui/material';

const data = [
  { icon: <HandshakeTwoToneIcon />, label: 'Bank vs Mrs Peters - Settled - chf 1.5M - 1 year' },
  { icon: <WorkspacePremiumTwoToneIcon />, label: 'Bank vs Mr Pertussi - Won - chf0 - 4 years' },
  { icon: <Public />, label: 'Bank vs Governnent - Public Case - chf 3.7M - 10 years' },
];

type Sender = 'user' | 'CommunityManager' | 'GraphicDesigner' | 'Writer' | 'Auditor';

const senderColors: Record<Sender, string> = {
  'user': '#d1e7dd',
  'CommunityManager': '#d4e2d4',
  'GraphicDesigner': '#f0e8e8',
  'Writer': '#add8e6',
  'Auditor': '#ff7f7f',
};


const FireNav = styled(List)<{ component?: React.ElementType }>({
  '& .MuiListItemButton-root': {
    paddingLeft: 24,
    paddingRight: 24,
  },
  '& .MuiListItemIcon-root': {
    minWidth: 0,
    marginRight: 16,
  },
  '& .MuiSvgIcon-root': {
    fontSize: 20,
  },
});

type Message = {
  sender: string;
  text: any;
};

type ChatProps = {
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  sendMessage: (message: string, agent: string) => void;
};

export default function Chat({ messages, setMessages, sendMessage }: ChatProps) {
  const [open, setOpen] = React.useState(true);
  const [message, setMessage] = React.useState<string>('');

  const handleSend = (message:string) => {
    setMessages([...messages, { sender: 'user', text: message }]);
    sendMessage(message, "chat");
  };

  return (
    <FireNav component="nav" disablePadding>
      <ListItemButton
        alignItems="flex-start"
        onClick={() => setOpen(!open)}
        sx={{
          px: 3,
          pt: 2.5,
          pb: open ? 0 : 2.5,
          '&:hover, &:focus': { '& #arrowdownicon': { opacity: open ? 1 : 0 } },
        }}
      >
        <ListItemIcon sx={{ my: 0, opacity: 1, class: "menuicon" }}>
          <LightbulbIcon />
        </ListItemIcon>
        <ListItemText
          primary="Chat"
          primaryTypographyProps={{
            fontSize: 15,
            fontWeight: 'medium',
            lineHeight: '20px',
            mb: '2px',
          }}
          secondary="What would you like the campaing to be about?"
          secondaryTypographyProps={{
            noWrap: true,
            fontSize: 12,
            lineHeight: '16px',
            color: open ? 'rgba(0,0,0,0)' : 'rgba(255,255,255,0.5)',
          }}
          sx={{ my: 0 }}
        />
        <KeyboardArrowDown
          id="arrowdownicon"
          sx={{
            mr: -1,
            opacity: 0,
            transform: open ? 'rotate(-180deg)' : 'rotate(0)',
            transition: '0.2s',
          }}
        />
      </ListItemButton>
      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 50px)' }}>
        <Container maxWidth={false} style={{ overflowY: 'auto', flex: '1 0 auto', maxHeight: 'calc(100vh - 150px)'}}>
          <div style={{ margin: '0 auto', fontFamily: "sans-serif" }}>
            {messages.map((message, index) => (
              <div key={index} style={{
                margin: '10px',
                padding: '10px',
                borderRadius: '10px',
                backgroundColor: senderColors[message.sender as Sender] || '#d4e2d4',
                alignSelf: message.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '80%',
                wordWrap: 'break-word'
              }}>
                <strong>{message.sender}:</strong> {message.text}
              </div>
            ))}
          </div>
        </Container>
        <Container maxWidth={false} style={{ height: '150px' }}>
          <Grid container spacing={1} alignItems="flex-end">
            <Grid item xs={11}>
              <TextField
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                fullWidth
                inputProps={{ style: { height: 'auto' } }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSend((e.target as HTMLInputElement).value);
                    setMessage('');
                  }
                }}
              />
            </Grid>
            <Grid item xs={1}>
              <Button style={{ height: '100%' }} onClick={() => {
                handleSend(message);
                setMessage('');
              }}>
                Send
              </Button>
            </Grid>
          </Grid>
        </Container>
      </div>
      )}
    </FireNav>
  );
}