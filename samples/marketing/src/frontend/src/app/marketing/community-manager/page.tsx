"use client";

import * as React from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import KeyboardArrowDown from '@mui/icons-material/KeyboardArrowDown';
import Public from '@mui/icons-material/Public';
import HandshakeTwoToneIcon from '@mui/icons-material/HandshakeTwoTone';
import WorkspacePremiumTwoToneIcon from '@mui/icons-material/WorkspacePremiumTwoTone';
import GavelIcon from '@mui/icons-material/Gavel';
import { styled } from '@mui/material/styles';
import { green, pink } from '@mui/material/colors';
import AppShortcut from '@mui/icons-material/AttachMoney';
import LoopIcon from '@mui/icons-material/Loop';
import { Paper, Card, CardContent, CardHeader, Typography } from '@mui/material';

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

type CommunityManagerProps = {
  article: string;
  setArticle: React.Dispatch<React.SetStateAction<string>>;
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  imgUrl: string;
};

export default function CommunityManager({ article, setArticle, open, setOpen, imgUrl }: CommunityManagerProps) {
  console.log(`[CommunityManager] Rendering.`);

  return (
    <Box sx={{ display: 'flex' }}>
      <FireNav component="nav" disablePadding>
        <Box
          sx={{
            //bgcolor: open ? 'rgba(71, 98, 130, 0.2)' : null,
            //pb: open ? 2 : 0,
          }}
        >
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
              <AppShortcut />
            </ListItemIcon>
            <ListItemText
              primary="Social Media posts"
              primaryTypographyProps={{
                fontSize: 15,
                fontWeight: 'medium',
                lineHeight: '20px',
                mb: '2px',
              }}
              secondary="Posts in social media"
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
            article === '' || article === null ? (
              <Box>
                <LoopIcon
                  sx={{
                    animation: "spin 2s linear infinite",
                    "@keyframes spin": {
                      "0%": {
                        transform: "rotate(360deg)",
                      },
                      "100%": {
                        transform: "rotate(0deg)",
                      },
                    },
                  }}
                />
              </Box>
            ) : (
              <Card>
                <CardContent>
                    <Typography variant="h5" component="div">
                      Social media posts on X
                    </Typography>
                    <p>{article}</p>
                    <p style={{ width: '100%', height: '100%' }}>
                      <img 
                        src={imgUrl} 
                        alt="placeholder" 
                        style={{ width: '100%', height: 'auto' }}/>
                    </p>
                    <p>{imgUrl}</p>
                  </CardContent>

              </Card>
            )
          )}
        </Box>
      </FireNav>
    </Box>
  );
}