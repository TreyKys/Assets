	public static string GetHTMLChatMessageSource(ConversationMessageDto msg)
	{
		short num = 1;
		if (num != 0)
		{
		}
		num = 0;
		int num2 = num;
		switch (num2)
		{
		default:
		{
			bool flag = default(bool);
			switch (0)
			{
			default:
			{
				Guid? employeePictureID = default(Guid?);
				string text5 = default(string);
				string text6 = default(string);
				string text7 = default(string);
				string text3 = default(string);
				string text2 = default(string);
				string text = default(string);
				string text4 = default(string);
				while (true)
				{
					object obj;
					string text9;
					string text8;
					switch (num2)
					{
					case 32:
						if (!flag)
						{
							num = 9;
							num2 = num;
						}
						else
						{
							num = 15;
							num2 = num;
						}
						continue;
					case 9:
						num = 12;
						num2 = num;
						continue;
					case 12:
						obj = string.Empty;
						goto IL_01cc;
					case 15:
						obj = "class=\"customer\"";
						goto IL_01cc;
					case 25:
						if (!flag)
						{
							num = 29;
							num2 = num;
							continue;
						}
						goto case 4;
					case 29:
						employeePictureID = msg.EmployeePictureID;
						num = 1;
						num2 = num;
						continue;
					case 1:
						if (!employeePictureID.HasValue)
						{
							num = 16;
							num2 = num;
						}
						else
						{
							num = 30;
							num2 = num;
						}
						continue;
					case 16:
						num = 22;
						num2 = num;
						continue;
					case 22:
						text9 = "<em><div class=\"avatar " + ((App.Context.CompanyCOID == "ABK") ? "ABKAvatar" : "JVBAvatar") + "\"><!-- Bank image --></div></em>";
						goto IL_0317;
					case 30:
						employeePictureID = msg.EmployeePictureID;
						text9 = "<em><div class=\"avatar employee-" + employeePictureID.ToString() + "\"><!-- Employee image --></div></em>";
						goto IL_0317;
					case 4:
						text5 = string.Empty;
						num = 13;
						num2 = num;
						continue;
					case 13:
						if (msg.Attachments != null)
						{
							num = 3;
							num2 = num;
							continue;
						}
						goto case 41;
					case 3:
						num = 14;
						num2 = num;
						continue;
					case 14:
						if (msg.Attachments.Any())
						{
							num = 27;
							num2 = num;
							continue;
						}
						goto case 41;
					case 27:
						num = 43;
						num2 = num;
						continue;
					case 43:
						text5 = msg.Attachments.Aggregate(text5, delegate(string A_0, AttachmentDto A_1)
						{
							short num4 = -985;
							short num5 = num4;
							num4 = -985;
							switch (num5 == num4)
							{
							default:
								num4 = 1;
								if (num4 != 0)
								{
								}
								num4 = 0;
								if (num4 != 0)
								{
								}
								return A_0 + GetHTMLChatAttachmentSource(A_1);
							}
						});
						num = 41;
						num2 = num;
						continue;
					case 41:
						text6 = string.Empty;
						num = 28;
						num2 = num;
						continue;
					case 28:
						if (msg.Documents != null)
						{
							num = 17;
							num2 = num;
							continue;
						}
						goto case 18;
					case 17:
						num = 7;
						num2 = num;
						continue;
					case 7:
						if (msg.Documents.Any())
						{
							num = 20;
							num2 = num;
							continue;
						}
						goto case 18;
					case 20:
						num = 26;
						num2 = num;
						continue;
					case 26:
						text6 = msg.Documents.Aggregate(text6, delegate(string A_0, DocumentDto A_1)
						{
							short num4 = -23244;
							short num5 = num4;
							num4 = -23244;
							switch (num5 == num4)
							{
							default:
								num4 = 0;
								if (num4 != 0)
								{
								}
								num4 = 1;
								if (num4 != 0)
								{
								}
								return A_0 + GetHTMLChatDocumentSource(A_1);
							}
						});
						num = 18;
						num2 = num;
						continue;
					case 18:
						text7 = string.Empty;
						num = 42;
						num2 = num;
						continue;
					case 42:
						if (msg.DocumentPackages != null)
						{
							num = 5;
							num2 = num;
							continue;
						}
						goto case 31;
					case 5:
						num = 24;
						num2 = num;
						continue;
					case 24:
					{
						num = 21846;
						short num3 = num;
						num = 21846;
						switch (num3 == num)
						{
						case false:
						case true:
							break;
						default:
							goto IL_062b;
						}
						goto case 14;
					}
					case 19:
						num = 37;
						num2 = num;
						continue;
					case 37:
						text7 = msg.DocumentPackages.Aggregate(text7, delegate(string A_0, DocumentPackageDto A_1)
						{
							short num4 = 27655;
							short num5 = num4;
							num4 = 27655;
							switch (num5 == num4)
							{
							default:
								num4 = 1;
								if (num4 != 0)
								{
								}
								num4 = 0;
								if (num4 != 0)
								{
								}
								return A_0 + GetHTMLChatDocumentPackageSource(A_1);
							}
						});
						num = 31;
						num2 = num;
						continue;
					case 31:
						num = 33;
						num2 = num;
						continue;
					case 33:
						if (flag)
						{
							num = 11;
							num2 = num;
						}
						else
						{
							text3 = msg.DisplaySenderFullName;
							num = 8;
							num2 = num;
						}
						continue;
					case 11:
						text3 = msg.DisplayReceiverFullName;
						num = 36;
						num2 = num;
						continue;
					case 36:
						if (!b(text3))
						{
							num = 10;
							num2 = num;
						}
						else
						{
							num = 40;
							num2 = num;
						}
						continue;
					case 10:
						num = 39;
						num2 = num;
						continue;
					case 39:
						text8 = Messages.Communication.MessageTo() + " ";
						goto IL_07f9;
					case 40:
						text8 = Messages.Communication.MessageToShortOffice();
						goto IL_07f9;
					case 8:
						if (c(text3))
						{
							num = 6;
							num2 = num;
						}
						else
						{
							num = 44;
							num2 = num;
						}
						continue;
					case 6:
						text2 = Messages.Communication.MessageFromHelpdesk() + " ";
						num = 23;
						num2 = num;
						continue;
					case 44:
						if (b(text3))
						{
							num = 21;
							num2 = num;
						}
						else
						{
							num = 2;
							num2 = num;
						}
						continue;
					case 21:
						text2 = Messages.Communication.MessageFromOffice();
						num = 45;
						num2 = num;
						continue;
					case 2:
						if (a(text3))
						{
							num = 35;
							num2 = num;
						}
						else
						{
							text2 = Messages.Communication.MessageFrom() + " ";
							num = 0;
							num2 = num;
						}
						continue;
					case 35:
						text2 = Messages.Communication.MessageFromShort();
						num = 34;
						num2 = num;
						continue;
					case 0:
					case 23:
					case 34:
					case 38:
					case 45:
						{
							return $"\n                    <li>\n                        {text}\n                        <span>{text2}{text3}</span><blockquote {text4}>{WebUtility.HtmlDecode(msg.Body)}{text5}{text6}{text7}</blockquote>\n                        <span>{msg.Date.ToString("dddd dd MMM yyyy HH:mm")}</span>\n                    </li>\n                ";
						}
						IL_07f9:
						text2 = text8;
						num = 38;
						num2 = num;
						continue;
						IL_062b:
						num = 0;
						if (num != 0)
						{
						}
						if (msg.DocumentPackages.Any())
						{
							num = 19;
							num2 = num;
							continue;
						}
						goto case 31;
						IL_0317:
						text = text9;
						num = 4;
						num2 = num;
						continue;
						IL_01cc:
						text4 = (string)obj;
						text = string.Empty;
						num = 25;
