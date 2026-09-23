using System;
using System.CodeDom.Compiler;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Runtime.CompilerServices;
using System.Threading;
using Newtonsoft.Json;

namespace BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts;

[GeneratedCode("NJsonSchema", "14.4.0.0 (NJsonSchema v11.3.2.0 (Newtonsoft.Json v13.0.0.0))")]
public class ConversationMessageDto : INotifyPropertyChanged
{
	private Guid a;

	private Guid b;

	private string c;

	private Guid? d;

	private string e;

	private Guid f;

	private Guid g;

	private string h;

	private Guid? i;

	private DateTime j;

	private DateTime? k;

	private DateTime? l;

	private DateTime? m;

	private string n;

	private string o;

	private string p;

	private string q;

	private List<AttachmentDto> r = new List<AttachmentDto>();

	private List<DocumentDto> s = new List<DocumentDto>();

	private List<DocumentPackageDto> t = new List<DocumentPackageDto>();

	private string u;

	private string v;

	private string w;

	private string x;

	[CompilerGenerated]
	private PropertyChangedEventHandler y;

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("messageID", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public Guid MessageID
	{
		get
		{
			short num = 350;
			short num2 = num;
			num = 350;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return a;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 1:
					switch (0)
					{
					default:
						goto end_IL_0026;
					case 0:
						break;
					}
					goto default;
				default:
					if (a != value)
					{
						num = 0;
						num2 = num;
						break;
					}
					return;
				case 0:
				{
					num = 16558;
					short num3 = num;
					num = 16558;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						num = 1;
						if (num != 0)
						{
						}
						a = value;
						RaisePropertyChanged("MessageID");
						num = 2;
						num2 = num;
						break;
					case false:
					case true:
						return;
					}
					break;
				}
				case 2:
					return;
					end_IL_0026:
					break;
				}
			}
		}
	}

	[JsonProperty("conversationID", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public Guid ConversationID
	{
		get
		{
			short num = 27015;
			short num2 = num;
			num = 27015;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return b;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 1:
					switch (0)
					{
					default:
						goto end_IL_0027;
					case 0:
						break;
					}
					goto default;
				default:
					if (b != value)
					{
						num = 0;
						num2 = num;
						break;
					}
					return;
				case 0:
				{
					num = -26001;
					short num3 = num;
					num = -26001;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						b = value;
						RaisePropertyChanged("ConversationID");
						break;
					case false:
					case true:
						break;
					}
					num = 2;
					num2 = num;
					break;
				}
				case 2:
					{
						num = 1;
						if (num == 0)
						{
						}
						return;
					}
					end_IL_0027:
					break;
				}
			}
		}
	}

	[JsonProperty("body", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string Body
	{
		get
		{
			short num = 14113;
			short num2 = num;
			num = 14113;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return c;
			}
		}
		set
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = 0;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 0:
					switch (0)
					{
					default:
						continue;
					case 0:
						break;
					}
					goto default;
				default:
					if (c != value)
					{
						num = 2;
						num2 = num;
						continue;
					}
					return;
				case 2:
					break;
				case 1:
					return;
				}
				while (true)
				{
					c = value;
					RaisePropertyChanged("Body");
					num = -9263;
					short num3 = num;
					num = -9263;
					switch (num3 == num)
					{
					case false:
					case true:
						continue;
					}
					break;
				}
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				num2 = num;
			}
		}
	}

	[JsonProperty("senderPartyID", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public Guid? SenderPartyID
	{
		get
		{
			short num = 28906;
			short num2 = num;
			num = 28906;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return d;
			}
		}
		set
		{
			int num = default(int);
			Guid? guid = default(Guid?);
			Guid? guid2 = default(Guid?);
			short num2;
			switch (0)
			{
			default:
				while (true)
				{
					switch (num)
					{
					case 7:
						goto IL_00be;
					case 0:
						d = value;
						RaisePropertyChanged("SenderPartyID");
						num2 = 1;
						num = num2;
						continue;
					case 1:
						return;
					case 3:
						num2 = 8;
						num = num2;
						continue;
					case 8:
						num2 = 1;
						if (num2 == 0)
						{
						}
						return;
					case 4:
						num2 = 5;
						num = num2;
						continue;
					case 5:
						num2 = 0;
						num = num2;
						continue;
					case 2:
						if (!(guid.GetValueOrDefault() != guid2.GetValueOrDefault()))
						{
							return;
						}
						goto case 5;
					case 6:
						goto IL_0234;
					}
					break;
					IL_0234:
					if (guid.HasValue)
					{
						num2 = 2;
						num = num2;
					}
					else
					{
						num2 = 3;
						num = num2;
					}
					continue;
					IL_00be:
					if (guid.HasValue == guid2.HasValue)
					{
						num2 = 6;
						num = num2;
						continue;
					}
					goto IL_00d1;
				}
				goto case 0;
			case 0:
				{
					guid = d;
					guid2 = value;
					num2 = 1155;
					short num3 = num2;
					num2 = 1155;
					switch (num3 == num2)
					{
					case false:
					case true:
						goto IL_00d1;
					}
					num2 = 0;
					if (num2 != 0)
					{
					}
					num2 = 7;
					num = num2;
					goto default;
				}
				IL_00d1:
				num2 = 4;
				num = num2;
				goto default;
			}
		}
	}

	[JsonProperty("senderType", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public string SenderType
	{
		get
		{
			short num = -7629;
			short num2 = num;
			num = -7629;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return e;
			}
		}
		set
		{
			short num = 3012;
			short num2 = num;
			num = 3012;
			int num3 = default(int);
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				num = 0;
				num3 = num;
				goto IL_00b4;
			case false:
			case true:
				{
					switch (0)
					{
					case 0:
						goto IL_00c6;
					}
					goto IL_00b4;
				}
				IL_00c6:
				if (e != value)
				{
					num = 1;
					num3 = num;
					goto IL_00b4;
				}
				break;
				IL_00b4:
				while (true)
				{
					switch (num3)
					{
					case 0:
						break;
					default:
						goto IL_00c6;
					case 1:
						e = value;
						RaisePropertyChanged("SenderType");
						num = 2;
						num3 = num;
						continue;
					case 2:
						return;
					}
					break;
				}
				goto case false;
			}
		}
	}

	[JsonProperty("conversationInitiatorPartyID", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public Guid ConversationInitiatorPartyID
	{
		get
		{
			short num = 28375;
			short num2 = num;
			num = 28375;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return f;
			}
		}
		set
		{
			short num = 0;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 0:
					switch (0)
					{
					default:
						goto end_IL_0025;
					case 0:
						break;
					}
					goto default;
				default:
				{
					if (!(f != value))
					{
						return;
					}
					num = -6556;
					short num3 = num;
					num = -6556;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						num = 1;
						num2 = num;
						break;
					case false:
					case true:
						return;
					}
					break;
				}
				case 1:
					f = value;
					RaisePropertyChanged("ConversationInitiatorPartyID");
					num = 2;
					num2 = num;
					break;
				case 2:
					{
						num = 1;
						if (num == 0)
						{
						}
						return;
					}
					end_IL_0025:
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("receiverPartyID", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public Guid ReceiverPartyID
	{
		get
		{
			short num = 23319;
			short num2 = num;
			num = 23319;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return g;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				num = 27625;
				short num3 = num;
				num = 27625;
				switch (num3 == num)
				{
				default:
					num = 0;
					if (num != 0)
					{
					}
					num = 1;
					if (num != 0)
					{
					}
					switch (num2)
					{
					case 1:
						switch (0)
						{
						default:
							goto end_IL_005f;
						case 0:
							break;
						}
						break;
					case 0:
						g = value;
						RaisePropertyChanged("ReceiverPartyID");
						num = 2;
						num2 = num;
						goto end_IL_005f;
					case 2:
						return;
					}
					if (!(g != value))
					{
						return;
					}
					goto case false;
				case false:
				case true:
					{
						num = 0;
						num2 = num;
						break;
					}
					end_IL_005f:
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("receiverType", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public string ReceiverType
	{
		get
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = -24809;
			short num2 = num;
			num = -24809;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				return h;
			}
		}
		set
		{
			while (true)
			{
				short num = 0;
				int num2 = num;
				while (true)
				{
					switch (num2)
					{
					case 0:
						num = 1;
						if (num != 0)
						{
						}
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						goto default;
					default:
						if (h != value)
						{
							num = 1;
							num2 = num;
							continue;
						}
						return;
					case 1:
						h = value;
						RaisePropertyChanged("ReceiverType");
						num = 2;
						num2 = num;
						continue;
					case 2:
						break;
					}
					break;
				}
				num = 14738;
				short num3 = num;
				num = 14738;
				switch (num3 == num)
				{
				case false:
				case true:
					continue;
				}
				num = 0;
				if (num == 0)
				{
				}
				return;
			}
		}
	}

	[JsonProperty("employeePictureID", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public Guid? EmployeePictureID
	{
		get
		{
			short num = 25215;
			short num2 = num;
			num = 25215;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return i;
			}
		}
		set
		{
			int num = default(int);
			Guid? guid = default(Guid?);
			Guid? guid2 = default(Guid?);
			while (true)
			{
				switch (0)
				{
				default:
					while (true)
					{
						short num2;
						switch (num)
						{
						case 2:
							goto IL_0057;
						case 7:
							return;
						case 3:
							num2 = 4;
							num = num2;
							continue;
						case 1:
							num2 = 8;
							num = num2;
							continue;
						case 8:
							num2 = 0;
							num = num2;
							continue;
						case 0:
							goto IL_016c;
						case 5:
							if (!(guid.GetValueOrDefault() != guid2.GetValueOrDefault()))
							{
								return;
							}
							goto case 8;
						case 6:
							goto IL_022c;
						case 4:
							return;
						}
						break;
						IL_022c:
						if (guid.HasValue)
						{
							num2 = 5;
							num = num2;
						}
						else
						{
							num2 = 3;
							num = num2;
						}
						continue;
						IL_016c:
						num2 = 27869;
						short num3 = num2;
						num2 = 27869;
						switch (num3 == num2)
						{
						case false:
						case true:
							break;
						default:
							num2 = 0;
							if (num2 != 0)
							{
							}
							i = value;
							RaisePropertyChanged("EmployeePictureID");
							num2 = 7;
							num = num2;
							continue;
						}
						goto end_IL_0001;
						IL_0057:
						if (guid.HasValue != guid2.HasValue)
						{
							num2 = 1;
							if (num2 != 0)
							{
							}
							num2 = 1;
							num = num2;
						}
						else
						{
							num2 = 6;
							num = num2;
						}
					}
					goto case 0;
				case 0:
					{
						guid = i;
						guid2 = value;
						short num2 = 2;
						num = num2;
						goto default;
					}
					end_IL_0001:
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("date", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public DateTime Date
	{
		get
		{
			short num = 29063;
			short num2 = num;
			num = 29063;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return j;
			}
		}
		set
		{
			while (true)
			{
				short num = 2;
				int num2 = num;
				while (true)
				{
					switch (num2)
					{
					case 2:
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						goto default;
					default:
						num = 1;
						if (num != 0)
						{
						}
						if (j != value)
						{
							num = 0;
							num2 = num;
							continue;
						}
						return;
					case 0:
						j = value;
						RaisePropertyChanged("Date");
						num = 1;
						num2 = num;
						continue;
					case 1:
						break;
					}
					break;
				}
				num = -27809;
				short num3 = num;
				num = -27809;
				switch (num3 == num)
				{
				case false:
				case true:
					continue;
				}
				num = 0;
				if (num == 0)
				{
				}
				return;
			}
		}
	}

	[JsonProperty("readDate", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public DateTime? ReadDate
	{
		get
		{
			short num = -20840;
			short num2 = num;
			num = -20840;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return k;
			}
		}
		set
		{
			short num = -10575;
			short num2 = num;
			num = -10575;
			int num3 = default(int);
			DateTime? dateTime = default(DateTime?);
			DateTime? dateTime2 = default(DateTime?);
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				switch (0)
				{
				case 0:
					goto IL_009e;
				}
				goto IL_0074;
			case false:
			case true:
				{
					num = 8;
					num3 = num;
					goto IL_0074;
				}
				IL_009e:
				dateTime = k;
				dateTime2 = value;
				num = 0;
				num3 = num;
				goto IL_0074;
				IL_0074:
				while (true)
				{
					switch (num3)
					{
					case 0:
						goto IL_00c1;
					case 6:
						k = value;
						RaisePropertyChanged("ReadDate");
						num = 7;
						num3 = num;
						continue;
					case 7:
						return;
					case 8:
						num = 4;
						num3 = num;
						continue;
					case 4:
						num = 6;
						num3 = num;
						continue;
					case 2:
						if (!(dateTime.GetValueOrDefault() != dateTime2.GetValueOrDefault()))
						{
							return;
						}
						goto case 4;
					case 3:
						goto IL_01eb;
					case 5:
						num = 1;
						if (num != 0)
						{
						}
						num = 1;
						num3 = num;
						continue;
					case 1:
						return;
					}
					break;
					IL_01eb:
					if (dateTime.HasValue)
					{
						num = 2;
						num3 = num;
					}
					else
					{
						num = 5;
						num3 = num;
					}
					continue;
					IL_00c1:
					if (dateTime.HasValue == dateTime2.HasValue)
					{
						num = 3;
						num3 = num;
						continue;
					}
					goto case false;
				}
				goto IL_009e;
			}
		}
	}

	[JsonProperty("archivedDate", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public DateTime? ArchivedDate
	{
		get
		{
			short num = 6684;
			short num2 = num;
			num = 6684;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return l;
			}
		}
		set
		{
			int num = default(int);
			DateTime? dateTime = default(DateTime?);
			DateTime? dateTime2 = default(DateTime?);
			short num2;
			switch (0)
			{
			default:
				while (true)
				{
					switch (num)
					{
					case 2:
						goto IL_00b8;
					case 8:
						l = value;
						RaisePropertyChanged("ArchivedDate");
						num2 = 1;
						num = num2;
						continue;
					case 1:
						return;
					case 3:
						goto IL_0121;
					case 7:
						num2 = 1;
						if (num2 == 0)
						{
						}
						return;
					case 4:
						num2 = 5;
						num = num2;
						continue;
					case 5:
						num2 = 8;
						num = num2;
						continue;
					case 6:
						if (!(dateTime.GetValueOrDefault() != dateTime2.GetValueOrDefault()))
						{
							return;
						}
						goto case 5;
					case 0:
						goto IL_021f;
					}
					break;
					IL_021f:
					if (dateTime.HasValue)
					{
						num2 = 6;
						num = num2;
					}
					else
					{
						num2 = 3;
						num = num2;
					}
					continue;
					IL_00b8:
					if (dateTime.HasValue != dateTime2.HasValue)
					{
						num2 = 4;
						num = num2;
					}
					else
					{
						num2 = 0;
						num = num2;
					}
				}
				goto case 0;
			case 0:
				{
					dateTime = l;
					dateTime2 = value;
					num2 = 28823;
					short num3 = num2;
					num2 = 28823;
					switch (num3 == num2)
					{
					case false:
					case true:
						goto IL_0121;
					}
					num2 = 0;
					if (num2 != 0)
					{
					}
					num2 = 2;
					num = num2;
					goto default;
				}
				IL_0121:
				num2 = 7;
				num = num2;
				goto default;
			}
		}
	}

	[JsonProperty("deletedDate", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public DateTime? DeletedDate
	{
		get
		{
			short num = 20954;
			short num2 = num;
			num = 20954;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return m;
			}
		}
		set
		{
			int num = default(int);
			DateTime? dateTime = default(DateTime?);
			DateTime? dateTime2 = default(DateTime?);
			switch (0)
			{
			default:
				while (true)
				{
					switch (num)
					{
					case 0:
						if (dateTime.HasValue != dateTime2.HasValue)
						{
							short num2 = 3;
							num = num2;
						}
						else
						{
							short num2 = 1;
							num = num2;
						}
						continue;
					case 5:
					{
						short num2 = 1;
						if (num2 != 0)
						{
						}
						num2 = -32679;
						short num3 = num2;
						num2 = -32679;
						switch (num3 == num2)
						{
						case false:
						case true:
							continue;
						}
						num2 = 0;
						if (num2 != 0)
						{
						}
						m = value;
						RaisePropertyChanged("DeletedDate");
						num2 = 2;
						num = num2;
						continue;
					}
					case 2:
						return;
					case 8:
					{
						short num2 = 4;
						num = num2;
						continue;
					}
					case 3:
					{
						short num2 = 7;
						num = num2;
						continue;
					}
					case 7:
					{
						short num2 = 5;
						num = num2;
						continue;
					}
					case 6:
						if (!(dateTime.GetValueOrDefault() != dateTime2.GetValueOrDefault()))
						{
							return;
						}
						goto case 7;
					case 1:
						if (dateTime.HasValue)
						{
							short num2 = 6;
							num = num2;
						}
						else
						{
							short num2 = 8;
							num = num2;
						}
						continue;
					case 4:
						return;
					}
					break;
				}
				goto case 0;
			case 0:
			{
				dateTime = m;
				dateTime2 = value;
				short num2 = 0;
				num = num2;
				goto default;
			}
			}
		}
	}

	[JsonProperty("messageType", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public string MessageType
	{
		get
		{
			short num = -14278;
			short num2 = num;
			num = -14278;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return n;
			}
		}
		set
		{
			while (true)
			{
				short num = 2;
				int num2 = num;
				while (true)
				{
					switch (num2)
					{
					case 2:
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						break;
					case 1:
						num = 1;
						if (num != 0)
						{
						}
						n = value;
						RaisePropertyChanged("MessageType");
						num = 0;
						num2 = num;
						continue;
					case 0:
						return;
					}
					num = 8543;
					short num3 = num;
					num = 8543;
					switch (num3 == num)
					{
					case false:
					case true:
						break;
					default:
						num = 0;
						if (num != 0)
						{
						}
						if (n != value)
						{
							num = 1;
							num2 = num;
							continue;
						}
						return;
					}
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("messageContentType", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public string MessageContentType
	{
		get
		{
			short num = 18188;
			short num2 = num;
			num = 18188;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return o;
			}
		}
		set
		{
			short num = 2;
			int num2 = num;
			while (true)
			{
				num = -32030;
				short num3 = num;
				num = -32030;
				switch (num3 == num)
				{
				case false:
				case true:
					return;
				}
				num = 0;
				if (num != 0)
				{
				}
				switch (num2)
				{
				case 2:
					num = 1;
					if (num != 0)
					{
					}
					switch (0)
					{
					default:
						goto end_IL_00c5;
					case 0:
						break;
					}
					goto default;
				default:
					if (o != value)
					{
						num = 0;
						num2 = num;
						break;
					}
					return;
				case 0:
					o = value;
					RaisePropertyChanged("MessageContentType");
					num = 1;
					num2 = num;
					break;
				case 1:
					return;
					end_IL_00c5:
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("receiverFullName", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public string ReceiverFullName
	{
		get
		{
			short num = 5850;
			short num2 = num;
			num = 5850;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return p;
			}
		}
		set
		{
			short num = 0;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 0:
					switch (0)
					{
					default:
						goto end_IL_0025;
					case 0:
						break;
					}
					goto default;
				default:
				{
					num = -3992;
					short num3 = num;
					num = -3992;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						if (p != value)
						{
							num = 2;
							num2 = num;
							goto end_IL_0025;
						}
						return;
					case false:
					case true:
						break;
					}
					goto IL_010d;
				}
				case 2:
					num = 1;
					if (num != 0)
					{
					}
					p = value;
					RaisePropertyChanged("ReceiverFullName");
					goto IL_010d;
				case 1:
					return;
					IL_010d:
					num = 1;
					num2 = num;
					break;
					end_IL_0025:
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("senderFullName", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public string SenderFullName
	{
		get
		{
			short num = -13835;
			short num2 = num;
			num = -13835;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return q;
			}
		}
		set
		{
			short num = -28276;
			short num2 = num;
			num = -28276;
			int num3;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				num3 = num;
				goto IL_008e;
			case false:
			case true:
				{
					num = 0;
					num3 = num;
					goto IL_008e;
				}
				IL_008e:
				while (true)
				{
					switch (num3)
					{
					case 1:
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						goto default;
					default:
						num = 1;
						if (num != 0)
						{
						}
						if (q != value)
						{
							num = 2;
							num3 = num;
							continue;
						}
						return;
					case 2:
						break;
					case 0:
						return;
					}
					break;
				}
				q = value;
				RaisePropertyChanged("SenderFullName");
				goto case false;
			}
		}
	}

	[Required]
	[JsonProperty("attachments", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public List<AttachmentDto> Attachments
	{
		get
		{
			short num = -22683;
			short num2 = num;
			num = -22683;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return r;
			}
		}
		set
		{
			short num = 0;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 0:
					switch (0)
					{
					default:
						goto end_IL_0025;
					case 0:
						break;
					}
					goto default;
				default:
					if (r == value)
					{
						return;
					}
					goto IL_0042;
				case 1:
					r = value;
					RaisePropertyChanged("Attachments");
					num = 2;
					num2 = num;
					break;
				case 2:
					{
						num = 25752;
						short num3 = num;
						num = 25752;
						switch (num3 == num)
						{
						case false:
						case true:
							break;
						default:
							num = 0;
							if (num != 0)
							{
							}
							num = 1;
							if (num == 0)
							{
							}
							return;
						}
						goto IL_0042;
					}
					IL_0042:
					num = 1;
					num2 = num;
					break;
					end_IL_0025:
					break;
				}
			}
		}
	}

	[JsonProperty("documents", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required]
	public List<DocumentDto> Documents
	{
		get
		{
			short num = -16113;
			short num2 = num;
			num = -16113;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return s;
			}
		}
		set
		{
			short num = 2;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 2:
					switch (0)
					{
					default:
						goto end_IL_0026;
					case 0:
						break;
					}
					goto default;
				default:
				{
					num = 1;
					if (num != 0)
					{
					}
					if (s == value)
					{
						return;
					}
					num = -5547;
					short num3 = num;
					num = -5547;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						num = 0;
						num2 = num;
						break;
					case false:
					case true:
						return;
					}
					break;
				}
				case 0:
					s = value;
					RaisePropertyChanged("Documents");
					num = 1;
					num2 = num;
					break;
				case 1:
					return;
					end_IL_0026:
					break;
				}
			}
		}
	}

	[JsonProperty("documentPackages", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required]
	public List<DocumentPackageDto> DocumentPackages
	{
		get
		{
			short num = -6805;
			short num2 = num;
			num = -6805;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return t;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 1:
					switch (0)
					{
					default:
						goto end_IL_002b;
					case 0:
						break;
					}
					goto default;
				default:
					if (t != value)
					{
						num = 2;
						num2 = num;
						break;
					}
					goto case 0;
				case 2:
					t = value;
					RaisePropertyChanged("DocumentPackages");
					num = 0;
					num2 = num;
					break;
				case 0:
					{
						num = 31533;
						short num3 = num;
						num = 31533;
						switch (num3 == num)
						{
						case false:
						case true:
							break;
						default:
							num = 0;
							if (num != 0)
							{
							}
							num = 1;
							if (num == 0)
							{
							}
							return;
						}
						goto default;
					}
					end_IL_002b:
					break;
				}
			}
		}
	}

	[JsonProperty("templateMergeContent", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string TemplateMergeContent
	{
		get
		{
			short num = 24229;
			short num2 = num;
			num = 24229;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return u;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 1:
					switch (0)
					{
					default:
						goto end_IL_002c;
					case 0:
						break;
					}
					goto default;
				default:
					if (u != value)
					{
						num = 2;
						num2 = num;
						break;
					}
					return;
				case 2:
					u = value;
					RaisePropertyChanged("TemplateMergeContent");
					num = 0;
					num2 = num;
					break;
				case 0:
					{
						num = 25637;
						short num3 = num;
						num = 25637;
						switch (num3 == num)
						{
						case false:
						case true:
							break;
						default:
							num = 1;
							if (num != 0)
							{
							}
							num = 0;
							if (num == 0)
							{
							}
							return;
						}
						goto case 2;
					}
					end_IL_002c:
					break;
				}
			}
		}
	}

	[JsonProperty("style", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string Style
	{
		get
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = -2269;
			short num2 = num;
			num = -2269;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				return v;
			}
		}
		set
		{
			short num = 18075;
			short num2 = num;
			num = 18075;
			switch (num2 == num)
			{
			case false:
			case true:
				return;
			}
			num = 0;
			if (num != 0)
			{
			}
			num = 1;
			if (num != 0)
			{
			}
			num = 0;
			int num3 = num;
			while (true)
			{
				switch (num3)
				{
				case 0:
					switch (0)
					{
					default:
						goto end_IL_00cb;
					case 0:
						break;
					}
					goto default;
				default:
					if (v != value)
					{
						num = 2;
						num3 = num;
						break;
					}
					return;
				case 2:
					v = value;
					RaisePropertyChanged("Style");
					num = 1;
					num3 = num;
					break;
				case 1:
					return;
					end_IL_00cb:
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("displayReceiverFullName", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public string DisplayReceiverFullName
	{
		get
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = -12410;
			short num2 = num;
			num = -12410;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				return w;
			}
		}
		set
		{
			short num = 2;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 2:
					switch (0)
					{
					default:
						goto end_IL_002c;
					case 0:
						break;
					}
					goto default;
				default:
					while (true)
					{
						if (w != value)
						{
							num = -27382;
							short num3 = num;
							num = -27382;
							switch (num3 == num)
							{
							case false:
							case true:
								continue;
							}
							break;
						}
						return;
					}
					num = 0;
					if (num != 0)
					{
					}
					num = 1;
					num2 = num;
					break;
				case 1:
					num = 1;
					if (num != 0)
					{
					}
					w = value;
					RaisePropertyChanged("DisplayReceiverFullName");
					num = 0;
					num2 = num;
					break;
				case 0:
					return;
					end_IL_002c:
					break;
				}
			}
		}
	}

	[JsonProperty("displaySenderFullName", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public string DisplaySenderFullName
	{
		get
		{
			short num = 4942;
			short num2 = num;
			num = 4942;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return x;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 1:
					switch (0)
					{
					default:
						goto end_IL_0026;
					case 0:
						break;
					}
					goto default;
				default:
					if (x != value)
					{
						num = 0;
						num2 = num;
						break;
					}
					return;
				case 0:
					x = value;
					RaisePropertyChanged("DisplaySenderFullName");
					num = 2;
					num2 = num;
					break;
				case 2:
					{
						num = 1;
						if (num != 0)
						{
						}
						num = -5316;
						short num3 = num;
						num = -5316;
						switch (num3 == num)
						{
						case false:
						case true:
							return;
						}
						num = 0;
						if (num == 0)
						{
						}
						return;
					}
					end_IL_0026:
					break;
				}
			}
		}
	}

	public event PropertyChangedEventHandler PropertyChanged
	{
		[CompilerGenerated]
		add
		{
			int num3 = default(int);
			PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
			switch (0)
			{
			default:
			{
				PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
				while (true)
				{
					short num = -16210;
					short num2 = num;
					num = -16210;
					switch (num2 == num)
					{
					case false:
					case true:
						return;
					}
					num = 0;
					if (num != 0)
					{
					}
					num = 1;
					if (num != 0)
					{
					}
					switch (num3)
					{
					case 1:
					{
						propertyChangedEventHandler2 = propertyChangedEventHandler;
						PropertyChangedEventHandler propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Combine(propertyChangedEventHandler2, value);
						propertyChangedEventHandler = Interlocked.CompareExchange(ref y, propertyChangedEventHandler3, propertyChangedEventHandler2);
						num = 0;
						num3 = num;
						continue;
					}
					case 0:
						if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
						{
							num = 2;
							num3 = num;
							continue;
						}
						goto case 1;
					case 2:
						return;
					}
					break;
				}
				goto case 0;
			}
			case 0:
			{
				propertyChangedEventHandler = y;
				short num = 1;
				num3 = num;
				goto default;
			}
			}
		}
		[CompilerGenerated]
		remove
		{
			int num3 = default(int);
			PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
			switch (0)
			{
			default:
			{
				PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
				while (true)
				{
					short num = 21917;
					short num2 = num;
					num = 21917;
					PropertyChangedEventHandler propertyChangedEventHandler3;
					switch (num2 == num)
					{
					default:
						num = 1;
						if (num != 0)
						{
						}
						num = 0;
						if (num != 0)
						{
						}
						switch (num3)
						{
						case 1:
							goto IL_00df;
						case 0:
							goto IL_0120;
						case 2:
							return;
						}
						break;
					case false:
					case true:
						goto IL_00df;
						IL_0120:
						if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
						{
							num = 2;
							num3 = num;
							continue;
						}
						goto IL_00df;
						IL_00df:
						propertyChangedEventHandler2 = propertyChangedEventHandler;
						propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Remove(propertyChangedEventHandler2, value);
						propertyChangedEventHandler = Interlocked.CompareExchange(ref y, propertyChangedEventHandler3, propertyChangedEventHandler2);
						num = 0;
						num3 = num;
						continue;
					}
					break;
				}
				goto case 0;
			}
			case 0:
			{
				propertyChangedEventHandler = y;
				short num = 1;
				num3 = num;
				goto default;
			}
			}
		}
	}

	protected virtual void RaisePropertyChanged([CallerMemberName] string propertyName = null)
	{
		short num = -10159;
		short num2 = num;
		num = -10159;
		int num3 = default(int);
		PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
		switch (num2 == num)
		{
		default:
			num = 0;
			if (num != 0)
			{
			}
			switch (0)
			{
			case 0:
				goto IL_0081;
			}
			goto case false;
		case false:
		case true:
			{
				while (true)
				{
					switch (num3)
					{
					case 2:
						if (propertyChangedEventHandler != null)
						{
							num = 0;
							num3 = num;
							continue;
						}
						return;
					case 0:
						propertyChangedEventHandler(this, new PropertyChangedEventArgs(propertyName));
						num = 1;
						num3 = num;
						continue;
					case 1:
						num = 1;
						if (num == 0)
						{
						}
						return;
					}
					break;
				}
				goto IL_0081;
			}
			IL_0081:
			propertyChangedEventHandler = y;
			num = 2;
			num3 = num;
			goto case false;
		}
	}
}
